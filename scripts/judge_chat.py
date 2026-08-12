#!/usr/bin/env python3
"""BUILD TIME. Reproduce the judge's chat invocation against a candidate GGUF.

INVOCATION FIDELITY
-------------------
The judging panel chats with the model live on the Standard Laptop profile. We cannot see
their interface, so this harness reproduces the closest thing we can prove: `llama-server`
from the OFFICIAL profiler image, at the official pinned llama.cpp ref, under the audit
memory and CPU constraints, driven through /v1/chat/completions with NO client-supplied
system message.

Every one of those choices is deliberate:
  - official image, not a native build, so the SIMD-disabled toolchain is in play and
    latency is felt the way a judge would feel it (COMPETITION.md section 6a)
  - --memory=7.5g --cpus=4, matching the audit sandbox
  - no system message, because a judge typing into a chat box does not send one, which is
    exactly what makes the GGUF's embedded template the only channel we control
  - NO -t FLAG. This previously passed `-t 4`, which was a fidelity violation: the judges'
    harness has no reason to pass it, so llama-server spawns threads from the host CPU
    count under a 4-CPU quota exactly as llama-bench does. "Correcting" the
    oversubscription would produce latency a judge will never experience, which is the
    opposite of what this harness exists for (COMPETITION.md section 9e-bis).

Results from this harness are an INTERNAL PROXY. They are not the judges' score and must
never be presented as one.

Usage:
    python3 scripts/judge_chat.py --model models/bakeoff/qwen3.5-2b-q4_k_m.gguf --apply-template-only
    python3 scripts/judge_chat.py --model <gguf> --questions competition/chat_probe.yaml --tag baked
"""
from __future__ import annotations

import argparse
import json
import shlex
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[1]
RUNS = REPO / "runs"
IMAGE = "adtc-profiler:latest"
AUDIT_MEMORY = "7.5g"
AUDIT_CPUS = "4"
PORT = 8080
CTX = 2048


def _server_script(model_in_container: str, payload_path: str, mode: str) -> str:
    """Bash run inside the container: start llama-server, drive it, print JSON."""
    return f"""
set -u
llama-server -m {shlex.quote(model_in_container)} -c {CTX} \
    --host 127.0.0.1 --port {PORT} -ngl 0 > /tmp/server.log 2>&1 &
SRV=$!
for i in $(seq 1 120); do
  curl -sf http://127.0.0.1:{PORT}/health > /dev/null 2>&1 && break
  sleep 2
done
if ! curl -sf http://127.0.0.1:{PORT}/health > /dev/null 2>&1; then
  echo '{{"error":"llama-server never became healthy"}}'
  tail -40 /tmp/server.log >&2
  exit 1
fi

python - {shlex.quote(payload_path)} {shlex.quote(mode)} <<'PYEOF'
import json, sys, time, urllib.request

payload_path, mode = sys.argv[1], sys.argv[2]
questions = json.load(open(payload_path))
BASE = "http://127.0.0.1:{PORT}"

def post(path, body, timeout=600):
    req = urllib.request.Request(
        BASE + path,
        data=json.dumps(body).encode(),
        headers={{"Content-Type": "application/json"}},
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())

def get(path):
    with urllib.request.urlopen(BASE + path, timeout=60) as r:
        return json.loads(r.read())

out = {{"props": {{}}, "applied_template": None, "turns": []}}

try:
    props = get("/props")
    out["props"] = {{
        "chat_template": props.get("chat_template"),
        "model_path": props.get("model_path"),
    }}
except Exception as e:
    out["props"] = {{"error": str(e)}}

# The decisive artefact: exactly what the model receives for a bare user turn.
try:
    out["applied_template"] = post(
        "/apply-template", {{"messages": [{{"role": "user", "content": "Hello"}}]}}
    ).get("prompt")
except Exception as e:
    out["applied_template"] = f"ERROR: {{e}}"

if mode == "apply-template-only":
    print(json.dumps(out))
    sys.exit(0)

for q in questions:
    t0 = time.time()
    try:
        # No system message. A judge typing in a chat box does not send one.
        resp = post("/v1/chat/completions", {{
            "messages": [{{"role": "user", "content": q["question"]}}],
            "max_tokens": 320,
            "temperature": 0.0,
            "seed": 42,
        }})
        elapsed = time.time() - t0
        msg = resp["choices"][0]["message"]
        choice = msg.get("content") or ""
        # Reasoning models put thinking in a separate field and can leave `content`
        # empty entirely. Recording both is the only way an empty answer is
        # diagnosable later instead of looking like a terse refusal.
        reasoning = msg.get("reasoning_content") or ""
        usage = resp.get("usage", {{}}) or {{}}
        out["turns"].append({{
            "id": q["id"],
            "category": q.get("category"),
            "question": q["question"],
            "answer": choice,
            "reasoning_chars": len(reasoning),
            "reasoning_head": reasoning[:400],
            "finish_reason": resp["choices"][0].get("finish_reason"),
            "seconds": round(elapsed, 2),
            "completion_tokens": usage.get("completion_tokens"),
            "prompt_tokens": usage.get("prompt_tokens"),
            "tokens_per_second": (
                round(usage["completion_tokens"] / elapsed, 2)
                if usage.get("completion_tokens") and elapsed > 0 else None
            ),
        }})
    except Exception as e:
        out["turns"].append({{
            "id": q["id"], "category": q.get("category"),
            "question": q["question"], "answer": None,
            "error": str(e), "seconds": round(time.time() - t0, 2),
        }})

print(json.dumps(out))
PYEOF
"""


def run(model: Path, questions: list[dict], mode: str, tag: str,
        host_class: str = "shared") -> dict:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    suffix = f"_{tag}" if tag else ""
    run_dir = RUNS / f"{stamp}_chat_{model.stem}{suffix}"
    run_dir.mkdir(parents=True, exist_ok=True)

    payload = run_dir / "questions.json"
    payload.write_text(json.dumps(questions), encoding="utf-8")

    script = _server_script("/m/" + model.name, "/work/questions.json", mode)

    cmd = [
        "docker", "run", "--rm",
        f"--memory={AUDIT_MEMORY}", f"--memory-swap={AUDIT_MEMORY}",
        f"--cpus={AUDIT_CPUS}",
        "-v", f"{model.parent.resolve()}:/m:ro",
        "-v", f"{run_dir.resolve()}:/work",
        "--entrypoint", "bash", IMAGE, "-c", script,
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    (run_dir / "stderr.log").write_text(proc.stderr or "", encoding="utf-8")

    stdout = (proc.stdout or "").strip()
    if not stdout:
        raise SystemExit(
            f"no output from the container (exit {proc.returncode}). "
            f"See {run_dir}/stderr.log"
        )
    # llama-server may print to stdout before our JSON; take the last JSON object.
    line = next(
        (ln for ln in reversed(stdout.splitlines()) if ln.strip().startswith("{")), None
    )
    if line is None:
        raise SystemExit(f"no JSON in container output. See {run_dir}/stderr.log")

    result = json.loads(line)
    # Record the fidelity state in the artefact itself, so a run measured under a
    # non-faithful invocation is self-identifying rather than relying on someone
    # remembering which week it was produced.
    result["_meta"] = {
        # Repo-relative: these records ship with the submission, and an absolute path
        # publishes a developer's home directory while telling a reader nothing.
        "run_dir": str(run_dir.relative_to(REPO)),
        "model": model.name,
        "image": IMAGE,
        "constraints": {"memory": AUDIT_MEMORY, "cpus": AUDIT_CPUS, "ctx": CTX},
        "recorded_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "label": "INTERNAL PROXY. Not the judges' score.",
        "host_class": host_class,
        "latency_quotable": host_class == "physical",
        "fidelity": {
            "llama_server_flags": ["-m", "-c", "--host", "--port", "-ngl"],
            "thread_flag_passed": False,
            "audit_faithful": True,
            "host_note": (
                "Latency is quotable ONLY from host_class=physical. On a shared VPS the "
                "core topology, cache and memory bandwidth are not the judges', and this "
                "host demonstrated 27.8% run-to-run spread on a fixed workload "
                "(COMPETITION.md section 9e)."
            ),
            "note": (
                "No -t: llama-server spawns threads from the host CPU count under the "
                "cgroup quota exactly as the judges' harness would. Latency here is "
                "quotable. Runs stamped FIDELITY_STALE.txt predate this and are not."
            ),
        },
    }
    (run_dir / "chat.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True, type=Path)
    ap.add_argument("--questions", type=Path, default=REPO / "competition" / "chat_probe.yaml")
    ap.add_argument("--apply-template-only", action="store_true",
                    help="just show what the model receives for a bare user turn")
    ap.add_argument("--tag", default="")
    ap.add_argument("--only", default="",
                    help="comma-separated probe ids, for a focused subset")
    ap.add_argument("--host-class", choices=("shared", "physical"), default="shared",
                    help="physical: a machine near the Standard Laptop spec, whose "
                         "latency is quotable. shared: a VPS, where latency is NOT "
                         "quotable because topology and neighbours are not the judges'.")
    args = ap.parse_args()

    if not args.model.exists():
        print(f"error: {args.model} not found", file=sys.stderr)
        return 2

    mode = "apply-template-only" if args.apply_template_only else "chat"
    questions: list[dict] = []
    if not args.apply_template_only:
        if not args.questions.exists():
            print(f"error: {args.questions} not found", file=sys.stderr)
            return 2
        questions = yaml.safe_load(args.questions.read_text(encoding="utf-8"))["questions"]
        if args.only:
            wanted = {q.strip() for q in args.only.split(",") if q.strip()}
            questions = [q for q in questions if q["id"] in wanted]
            missing = wanted - {q["id"] for q in questions}
            if missing:
                print(f"error: unknown probe id(s): {sorted(missing)}", file=sys.stderr)
                return 2

    result = run(args.model, questions, mode, args.tag, args.host_class)

    print(f"model: {args.model.name}")
    print(f"run:   {result['_meta']['run_dir']}")
    print("\n=== prompt the model actually receives for a bare user turn ===")
    print(result.get("applied_template"))

    if mode == "apply-template-only":
        return 0

    print(f"\n=== {len(result['turns'])} turns (INTERNAL PROXY) ===")
    for turn in result["turns"]:
        if turn.get("error"):
            print(f"\n[{turn['id']}] {turn['category']}  ERROR: {turn['error']}")
            continue
        print(f"\n[{turn['id']}] {turn['category']}  "
              f"{turn['seconds']}s  {turn.get('tokens_per_second')} tok/s")
        print(f"  Q: {turn['question']}")
        answer = (turn['answer'] or '').strip().replace("\n", "\n     ")
        print(f"  A: {answer[:700]}")

    times = [t["seconds"] for t in result["turns"] if t.get("seconds")]
    if times:
        median = sorted(times)[len(times) // 2]
        if args.host_class == "physical":
            print(f"\nmedian turn latency: {median}s (as a judge would experience it)")
        else:
            print(f"\nmedian turn latency: {median}s  **NOT QUOTABLE**")
            print("  host_class=shared. This VPS is not the judges' topology and shows "
                  "27.8% spread on a fixed workload.")
            print("  Re-run with --host-class physical on the O-12 machine before any "
                  "latency figure is used.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
