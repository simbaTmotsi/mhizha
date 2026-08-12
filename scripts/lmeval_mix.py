#!/usr/bin/env python3
"""BUILD TIME. Run the lm-eval task mix over bake-off candidates. INTERNAL PROXY ONLY.

WHAT THIS IS AND IS NOT
-----------------------
`S_acc` is scored entirely by judges chatting with the live model. We never submit an
accuracy number (COMPETITION.md section 4). This mix exists to RANK candidates against
each other, and every figure it produces is labelled INTERNAL PROXY wherever it appears.

WHY A MIX RATHER THAN THE PROFILER'S DEFAULT arc_easy
-----------------------------------------------------
The real evaluation set is hidden. Ranking six models on one easy science task risks
ranking them on a quirk of that task. Two ARC tasks give general reasoning at two
difficulties; two MMLU subsets are the closest available proxy for the agriculture domain
(biology and nutrition). None of them is agronomy, and the report must say so.

WHICH IMAGE
-----------
Accuracy is loglikelihood arithmetic over logits and should be build-invariant, so the
native AVX2 image is permitted for wall-clock reasons. That permission is GATED on the
O-09 spot check (`--spot-check`), which runs one candidate through both images and
compares scores. If they disagree beyond a tolerance, every accuracy run moves back
in-image and the sweep simply takes longer.

Usage:
    python3 scripts/lmeval_mix.py --spot-check --candidate qwen3.5-0.8b-q4_k_m
    python3 scripts/lmeval_mix.py --candidates all --image adtc-native-acc:latest
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[1]
RUNS = REPO / "runs"
BAKEOFF = REPO / "models" / "bakeoff"
MANIFEST = REPO / "competition" / "candidates.yaml"
HF_CACHE = REPO / ".cache" / "huggingface"

OFFICIAL_IMAGE = "adtc-profiler:latest"
NATIVE_ACC_IMAGE = "adtc-native-acc:latest"

# The mix. Two ARC difficulties plus the two MMLU subsets closest to the agriculture
# domain. Deliberately small and fixed: changing it mid-sweep would make candidates
# incomparable.
DEFAULT_TASKS = "arc_easy,arc_challenge,mmlu_high_school_biology,mmlu_nutrition"

# Spot-check tolerance. Loglikelihood ranking should be bit-comparable across builds;
# anything beyond this means the builds are not interchangeable for scoring.
SPOT_TOLERANCE = 0.02

AUDIT_MEMORY = "7.5g"
AUDIT_CPUS = "4"


def load_ids(spec: str) -> list[str]:
    manifest = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
    known = [c["id"] for c in manifest["candidates"]]
    if spec == "all":
        return known
    wanted = [s.strip() for s in spec.split(",") if s.strip()]
    unknown = [w for w in wanted if w not in known and w != manifest["smoke"]["id"]]
    if unknown:
        raise SystemExit(f"unknown candidate(s): {unknown}")
    return wanted


def run_in_image(candidate: str, image: str, tasks: str, limit: int, seed: int,
                 timeout_s: int) -> dict:
    model = BAKEOFF / f"{candidate}.gguf"
    if not model.exists():
        return {"error": f"{model} not found"}
    HF_CACHE.mkdir(parents=True, exist_ok=True)

    cmd = [
        "docker", "run", "--rm",
        f"--memory={AUDIT_MEMORY}", f"--memory-swap={AUDIT_MEMORY}",
        f"--cpus={AUDIT_CPUS}",
        "-v", f"{BAKEOFF}:/m:ro",
        "-v", f"{REPO / 'scripts'}:/s:ro",
        "-v", f"{HF_CACHE}:/root/.cache/huggingface",
        "-e", "HF_DATASETS_TRUST_REMOTE_CODE=1",
        "--entrypoint", "python", image,
        "/s/lmeval_inner.py", f"/m/{candidate}.gguf", tasks, str(limit), str(seed),
    ]
    # Host state either side of the run. The first sweep could not attribute its own
    # schedule miss because it logged none of this: wall time alone cannot distinguish a
    # bad estimate from a degraded host. Accuracy is unaffected either way, since
    # loglikelihood scores are deterministic given the seed, but the ETA is not.
    import importlib.util as _ilu

    _spec = _ilu.spec_from_file_location("_bench", REPO / "scripts" / "bench_screened.py")
    _bench = _ilu.module_from_spec(_spec)
    _spec.loader.exec_module(_bench)

    cpu_before = _bench.read_cpu_times()
    runq_before = _bench.read_runnable()
    started = time.time()
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_s)
    elapsed = time.time() - started
    cpu_after = _bench.read_cpu_times()
    host = {
        "steal_pct": round(_bench.steal_percent(cpu_before, cpu_after), 3),
        "runnable_before": runq_before,
        "runnable_after": _bench.read_runnable(),
    }

    line = next((ln for ln in reversed((proc.stdout or "").splitlines())
                 if ln.strip().startswith("{")), None)
    if line is None:
        return {"error": f"no JSON from container (exit {proc.returncode})",
                "stderr_tail": (proc.stderr or "")[-1200:],
                "wall_seconds": round(elapsed, 1), "host": host}
    result = json.loads(line)
    result["wall_seconds"] = round(elapsed, 1)
    result["image"] = image
    result["host"] = host
    return result


def spot_check(candidate: str, tasks: str, limit: int, seed: int, timeout_s: int) -> int:
    """O-09: do the two builds agree on accuracy? Gates use of the native image."""
    print(f"O-09 spot check on {candidate}")
    print(f"  tasks: {tasks}  limit: {limit}\n")

    print(f"  [1/2] {OFFICIAL_IMAGE} …", flush=True)
    official = run_in_image(candidate, OFFICIAL_IMAGE, tasks, limit, seed, timeout_s)
    print(f"        {json.dumps(official.get('tasks', official))[:200]}")
    print(f"        wall {official.get('wall_seconds')}s")

    print(f"  [2/2] {NATIVE_ACC_IMAGE} …", flush=True)
    native = run_in_image(candidate, NATIVE_ACC_IMAGE, tasks, limit, seed, timeout_s)
    print(f"        {json.dumps(native.get('tasks', native))[:200]}")
    print(f"        wall {native.get('wall_seconds')}s")

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = RUNS / f"{stamp}_spotcheck_{candidate}"
    out_dir.mkdir(parents=True, exist_ok=True)

    verdict, notes = "native-permitted", []
    if official.get("error") or native.get("error"):
        verdict = "inconclusive"
        notes.append(f"official error: {official.get('error')}; native error: {native.get('error')}")
    else:
        for task, o in official.get("tasks", {}).items():
            n = native.get("tasks", {}).get(task, {})
            if "score" not in o or "score" not in n:
                verdict = "inconclusive"
                notes.append(f"{task}: missing score in one build")
                continue
            delta = abs(o["score"] - n["score"])
            notes.append(f"{task}: official {o['score']:.4f} vs native {n['score']:.4f} "
                         f"(delta {delta:.4f})")
            if delta > SPOT_TOLERANCE:
                verdict = "native-REJECTED"

    speedup = None
    if official.get("eval_seconds") and native.get("eval_seconds"):
        speedup = round(official["eval_seconds"] / native["eval_seconds"], 2)

    record = {
        "candidate": candidate, "tasks": tasks, "limit": limit, "seed": seed,
        "tolerance": SPOT_TOLERANCE, "verdict": verdict, "notes": notes,
        "eval_speedup_native": speedup,
        "official": official, "native": native,
        "label": "INTERNAL PROXY. Gates O-09 only.",
    }
    (out_dir / "spotcheck.json").write_text(json.dumps(record, indent=2) + "\n",
                                            encoding="utf-8")
    print("\n" + "=" * 72)
    for note in notes:
        print(f"  {note}")
    if speedup:
        print(f"  native eval is {speedup}x faster")
    print(f"\n  VERDICT: {verdict}")
    if verdict == "native-REJECTED":
        print("  Accuracy differs across builds beyond tolerance. Run the whole sweep")
        print("  in the official image; it will simply take longer.")
    print("=" * 72)
    print(f"wrote {out_dir}/spotcheck.json")
    return 0 if verdict == "native-permitted" else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--candidates", default="")
    ap.add_argument("--candidate", default="", help="single candidate, for --spot-check")
    ap.add_argument("--tasks", default=DEFAULT_TASKS)
    ap.add_argument("--limit", type=int, default=50)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--image", default=OFFICIAL_IMAGE)
    ap.add_argument("--timeout", type=int, default=14400, help="per-candidate seconds")
    ap.add_argument("--spot-check", action="store_true")
    ap.add_argument("--tag", default="")
    args = ap.parse_args()

    if args.spot_check:
        return spot_check(args.candidate or "qwen3.5-0.8b-q4_k_m",
                          args.tasks, args.limit, args.seed, args.timeout)

    if not args.candidates:
        print("error: --candidates required (or --spot-check)", file=sys.stderr)
        return 2

    ids = load_ids(args.candidates)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    suffix = f"_{args.tag}" if args.tag else ""
    out_dir = RUNS / f"{stamp}_lmeval{suffix}"
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"candidates: {len(ids)}")
    print(f"tasks:      {args.tasks}")
    print(f"limit:      {args.limit}   seed: {args.seed}")
    print(f"image:      {args.image}")
    print("\nINTERNAL PROXY. S_acc is judge-scored; this ranks candidates only.\n")

    results: dict[str, dict] = {}
    for i, candidate in enumerate(ids, start=1):
        print(f"[{i}/{len(ids)}] {candidate} …", flush=True)
        try:
            row = run_in_image(candidate, args.image, args.tasks, args.limit,
                               args.seed, args.timeout)
        except subprocess.TimeoutExpired:
            row = {"error": f"timed out after {args.timeout}s"}
        results[candidate] = row
        if row.get("error"):
            print(f"        ERROR {row['error']}")
        else:
            per_task = "  ".join(
                f"{t}={v.get('score')}" for t, v in row.get("tasks", {}).items()
            )
            print(f"        mean {row.get('mean_score')}   {per_task}")
            print(f"        wall {row.get('wall_seconds')}s")
        # Write after every candidate: a sweep this long must not lose finished work.
        (out_dir / "lmeval.json").write_text(
            json.dumps({
                "recorded_at": stamp, "tasks": args.tasks, "limit": args.limit,
                "seed": args.seed, "image": args.image,
                "label": "INTERNAL PROXY. Not the judges' score.",
                "results": results,
            }, indent=2) + "\n", encoding="utf-8")

    print("\n" + "=" * 76)
    print(f"  {'candidate':32s} {'mean':>7s}  per-task")
    for candidate in ids:
        row = results[candidate]
        if row.get("error"):
            print(f"  {candidate:32s} {'ERROR':>7s}  {row['error'][:40]}")
            continue
        per_task = " ".join(f"{v.get('score')}" for v in row.get("tasks", {}).values())
        print(f"  {candidate:32s} {row.get('mean_score'):>7}  {per_task}")
    print("=" * 76)
    print(f"wrote {out_dir}/lmeval.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
