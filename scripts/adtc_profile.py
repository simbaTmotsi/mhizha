#!/usr/bin/env python3
"""BUILD TIME. Run the official ADTC profiler and archive one tagged result.

Deliberately NOT under src/mhizha/. This is developer tooling for a competition
submission, not product code: nothing here ships to a phone, and keeping it out of the
package keeps tests/test_offline.py's import scan meaningful for the code that does.

What this adds over calling `adtc-profiler` directly:

  1. Runs inside the official Docker image, constrained to --memory=7.5g --cpus=4, so a
     47 GB / 12 core workstation produces numbers comparable to the 8 GB / 4 vCPU audit
     box instead of flattering ones.
  2. Assembles a throwaway submission directory per candidate, so one repo can profile
     six models without six copies of metadata.json drifting apart.
  3. Computes the published score components locally, so a bake-off row is scored the
     same way the leaderboard scores it.
  4. Hard-fails here on thermal breach or OOM, so a failure happens on this machine and
     never in the judges' sandbox.
  5. Archives everything under runs/<run_id>/ tagged with model, config, and git hash.

Usage:
    python3 scripts/adtc_profile.py --candidate smollm2-135m-instruct-q4_k_m --skip-accuracy
    python3 scripts/adtc_profile.py --candidate llama-3.2-1b-instruct-q4_k_m
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[1]
RUNS = REPO / "runs"
MANIFEST = REPO / "competition" / "candidates.yaml"
BAKEOFF_DIR = REPO / "models" / "bakeoff"
IMAGE = "adtc-profiler:latest"

# Retrieved from vendor/adtc-profiler/README.md. Fixed constants, not relative to
# other entrants. Mirrored in competition/candidates.yaml: change both together.
TPS_REFERENCE = 15.0
RAM_LIMIT_GB = 7.0
THERMAL_LIMIT_C = 85.0

# Retrieved from the template README: the audit sandbox is 4 vCPU / 8 GB, and the
# profiler's own docker instructions use --memory=7.5g.
AUDIT_MEMORY = "7.5g"
AUDIT_CPUS = "4"


class ProfileError(RuntimeError):
    """The profiling run could not produce a trustworthy result."""


def load_manifest() -> dict:
    return yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))


def find_candidate(manifest: dict, candidate_id: str) -> dict:
    rows = list(manifest.get("candidates") or [])
    smoke = manifest.get("smoke")
    if smoke:
        rows.append(smoke)
    for row in rows:
        if row["id"] == candidate_id:
            return row
    known = ", ".join(r["id"] for r in rows)
    raise ProfileError(f"unknown candidate {candidate_id!r}. Known: {known}")


def git_sha() -> str:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short=12", "HEAD"],
            cwd=REPO, capture_output=True, text=True, check=True, timeout=5,
        )
        return out.stdout.strip()
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
        # Recorded honestly rather than papered over: a run with no git SHA cannot be
        # tied to a code state, and COMPETITION.md O-01 tracks fixing it.
        return "no-git"


def os_tuning() -> dict:
    """Capture the host tuning that affects the numbers, so the report can state it."""
    def read(path: str) -> str | None:
        try:
            return Path(path).read_text(encoding="utf-8").strip()
        except OSError:
            return None

    return {
        "vm.swappiness": read("/proc/sys/vm/swappiness"),
        "vm.overcommit_memory": read("/proc/sys/vm/overcommit_memory"),
        "transparent_hugepage": read("/sys/kernel/mm/transparent_hugepage/enabled"),
        "host_cpu_count": subprocess.run(
            ["nproc"], capture_output=True, text=True, check=False
        ).stdout.strip(),
        "mlock_enabled_in_profile": True,
        "note": (
            "The profiler drives llama-bench itself and does not read our config, so "
            "mlock and thread count here describe the product-side laptop_8gb profile, "
            "not flags passed to llama-bench. llama-bench is pinned -ngl 0 by the "
            "profiler and inherits the container's 4 CPUs."
        ),
    }


def build_submission_dir(run_dir: Path, candidate: dict, model_src: Path) -> Path:
    """Assemble a throwaway submission directory for this one candidate."""
    sub = run_dir / "submission"
    (sub / "model").mkdir(parents=True, exist_ok=True)

    metadata = json.loads((REPO / "metadata.json").read_text(encoding="utf-8"))
    model_name = f"{candidate['id']}.gguf"
    metadata["model"]["name"] = candidate["label"]
    metadata["model"]["parameters_estimate"] = candidate["params_estimate"]
    metadata["model"]["quantization"] = f"GGUF {candidate['quant']}"
    metadata["_runtime"]["model_path"] = f"model/{model_name}"
    (sub / "metadata.json").write_text(
        json.dumps(metadata, indent=2) + "\n", encoding="utf-8"
    )

    # Hardlink where possible: a 2.6 GB copy per run wastes disk for no benefit.
    dest = sub / "model" / model_name
    if not dest.exists():
        try:
            dest.hardlink_to(model_src)
        except (OSError, AttributeError):
            shutil.copy2(model_src, dest)
    return sub


def run_profiler(sub_dir: Path, run_dir: Path, *, skip_accuracy: bool,
                 task: str, limit: int, seed: int) -> tuple[int, str]:
    """Invoke the official profiler in Docker under audit-like constraints."""
    out_host = run_dir / "submission.json"
    cmd = [
        "docker", "run", "--rm",
        f"--memory={AUDIT_MEMORY}",
        # Without this, Docker grants swap equal to memory, so an over-budget model
        # swaps instead of OOM-ing and the run silently misreports as a success.
        f"--memory-swap={AUDIT_MEMORY}",
        f"--cpus={AUDIT_CPUS}",
        "-v", f"{sub_dir}:/submission:ro",
        "-v", f"{run_dir}:/artifacts",
        IMAGE, "run",
        "--submission", "/submission",
        "--mode", "participant",
        "--output", "/artifacts/submission.json",
        "--seed", str(seed),
    ]
    if skip_accuracy:
        cmd.append("--skip-accuracy")
    else:
        cmd += ["--accuracy-task", task, "--accuracy-limit", str(limit)]

    print(f"  $ {' '.join(cmd)}\n")
    proc = subprocess.run(cmd, capture_output=True, text=True)
    log = (proc.stdout or "") + (proc.stderr or "")
    (run_dir / "profiler.log").write_text(log, encoding="utf-8")
    print(log.strip())

    if proc.returncode == 137:
        raise ProfileError(
            f"OOM: the container was killed at {AUDIT_MEMORY}. In the judges' sandbox "
            "this is a DISQUALIFICATION, not a bad score. This candidate is out unless "
            "a smaller quantization fits."
        )
    if proc.returncode != 0:
        raise ProfileError(f"profiler exited {proc.returncode}. See {run_dir}/profiler.log")
    if not out_host.exists():
        raise ProfileError(f"profiler wrote no report to {out_host}")
    return proc.returncode, log


def score(report: dict) -> dict:
    """Compute the published leaderboard components from a profiler report.

    S_total = 0.50*S_acc + 0.30*S_perf + 0.20*S_eff - P_thermal
    """
    tps = float(report["throughput"]["tokens_per_second_generation"])
    peak_rss_gb = float(report["memory"]["peak_rss_mb"]) / 1024.0
    thermal = report.get("cpu_thermal") or {}
    temp = thermal.get("core_temp_c_peak")
    throttled = bool(thermal.get("throttled"))

    s_perf = min(tps / TPS_REFERENCE, 1.0) * 100.0
    s_eff = max(0.0, (RAM_LIMIT_GB - peak_rss_gb) / RAM_LIMIT_GB) * 100.0

    acc_rows = report.get("accuracy") or []
    s_acc = float(acc_rows[0]["score"]) * 100.0 if acc_rows else None

    penalty = 10.0 if (throttled or (temp is not None and temp >= THERMAL_LIMIT_C)) else 0.0

    known = 0.30 * s_perf + 0.20 * s_eff - penalty
    total = (0.50 * s_acc + known) if s_acc is not None else None

    return {
        "tokens_per_second": round(tps, 2),
        "peak_rss_mb": round(peak_rss_gb * 1024, 2),
        "peak_rss_gb": round(peak_rss_gb, 3),
        "core_temp_c_peak": temp,
        "throttled": throttled,
        "s_acc": round(s_acc, 2) if s_acc is not None else None,
        "s_perf": round(s_perf, 2),
        "s_eff": round(s_eff, 2),
        "p_thermal": penalty,
        "s_total": round(total, 2) if total is not None else None,
        "s_total_excluding_accuracy": round(known, 2),
        "accuracy_measured": s_acc is not None,
        "tps_headroom_wasted": round(max(0.0, tps - TPS_REFERENCE), 2),
    }


def check_hard_fails(scored: dict, report: dict) -> list[str]:
    """Fail here so the judges' sandbox never sees it."""
    failures = []
    if scored["throttled"] or (
        scored["core_temp_c_peak"] is not None
        and scored["core_temp_c_peak"] >= THERMAL_LIMIT_C
    ):
        failures.append(
            f"THERMAL: peak {scored['core_temp_c_peak']} C >= {THERMAL_LIMIT_C} C. "
            "That is a 10 point penalty on the leaderboard."
        )
    if scored["peak_rss_gb"] > RAM_LIMIT_GB:
        failures.append(
            f"MEMORY: peak RSS {scored['peak_rss_gb']:.2f} GB exceeds the "
            f"{RAM_LIMIT_GB} GB limit. S_eff is 0 and OOM risk in audit is real."
        )
    tput = report.get("throughput") or {}
    if not tput.get("tokens_per_second_generation"):
        failures.append("THROUGHPUT: zero or missing TPS is an automatic compare failure.")
    return failures


def main() -> int:
    ap = argparse.ArgumentParser(description="Run the official ADTC profiler, archived.")
    ap.add_argument("--candidate", required=True, help="id from competition/candidates.yaml")
    ap.add_argument("--tag", default="", help="extra label for the run directory")
    ap.add_argument("--skip-accuracy", action="store_true",
                    help="fast smoke loop; final numbers must come from a full run")
    ap.add_argument("--accuracy-task", default="arc_easy")
    ap.add_argument("--accuracy-limit", type=int, default=50)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    try:
        manifest = load_manifest()
        candidate = find_candidate(manifest, args.candidate)
    except ProfileError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    model_src = BAKEOFF_DIR / f"{candidate['id']}.gguf"
    if not model_src.exists():
        print(
            f"error: {model_src} not found.\n"
            f"  Fetch it first: bash scripts/fetch_candidates.sh {candidate['id']}",
            file=sys.stderr,
        )
        return 2

    if not shutil.which("docker"):
        print("error: docker not found. See COMPETITION.md section 6.", file=sys.stderr)
        return 2

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    sha = git_sha()
    suffix = f"_{args.tag}" if args.tag else ""
    run_id = f"{stamp}_{candidate['id']}_{sha}{suffix}"
    run_dir = RUNS / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    print(f"run_id: {run_id}")
    print(f"model:  {model_src.name} ({model_src.stat().st_size / 1048576:.0f} MB)")
    print(f"limits: --memory={AUDIT_MEMORY} --cpus={AUDIT_CPUS}")
    print(f"accuracy: {'SKIPPED' if args.skip_accuracy else args.accuracy_task}\n")

    sub_dir = build_submission_dir(run_dir, candidate, model_src)

    try:
        run_profiler(
            sub_dir, run_dir,
            skip_accuracy=args.skip_accuracy,
            task=args.accuracy_task, limit=args.accuracy_limit, seed=args.seed,
        )
    except ProfileError as exc:
        (run_dir / "run.json").write_text(
            json.dumps({"run_id": run_id, "candidate": candidate["id"],
                        "status": "failed", "error": str(exc)}, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"\nFAILED: {exc}", file=sys.stderr)
        return 1

    report = json.loads((run_dir / "submission.json").read_text(encoding="utf-8"))
    scored = score(report)
    failures = check_hard_fails(scored, report)

    record = {
        "run_id": run_id,
        "recorded_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "status": "failed" if failures else "ok",
        "candidate": {k: candidate.get(k) for k in
                      ("id", "label", "repo", "file", "params_estimate", "quant", "licence")},
        "model_sha256_source": "competition/candidate_hashes.txt",
        "git_commit_sha": sha,
        "docker_image": IMAGE,
        "constraints": {"memory": AUDIT_MEMORY, "cpus": AUDIT_CPUS},
        "accuracy_task": None if args.skip_accuracy else args.accuracy_task,
        "accuracy_limit": None if args.skip_accuracy else args.accuracy_limit,
        "seed": args.seed,
        "os_tuning": os_tuning(),
        "scoring_constants": {
            "tps_reference": TPS_REFERENCE,
            "ram_limit_gb": RAM_LIMIT_GB,
            "thermal_limit_c": THERMAL_LIMIT_C,
            "source": "vendor/adtc-profiler/README.md (retrieved)",
        },
        "score": scored,
        "hard_fails": failures,
        "environment": report.get("environment"),
        "model_info": report.get("model_info"),
    }
    (run_dir / "run.json").write_text(
        json.dumps(record, indent=2) + "\n", encoding="utf-8"
    )

    print("\n" + "=" * 68)
    print(f"  tokens/sec      {scored['tokens_per_second']:>10}   "
          f"(reference {TPS_REFERENCE}, above it earns nothing)")
    print(f"  peak RSS        {scored['peak_rss_mb']:>10} MB "
          f"({scored['peak_rss_gb']:.2f} GB of {RAM_LIMIT_GB} GB)")
    print(f"  core temp peak  {str(scored['core_temp_c_peak']):>10}")
    print(f"  S_perf (30%)    {scored['s_perf']:>10.2f}")
    print(f"  S_eff  (20%)    {scored['s_eff']:>10.2f}")
    print(f"  S_acc  (50%)    {str(scored['s_acc']):>10}"
          f"{'   NOT MEASURED (--skip-accuracy)' if scored['s_acc'] is None else ''}")
    print(f"  P_thermal       {scored['p_thermal']:>10.2f}")
    print(f"  S_total         {str(scored['s_total']):>10}")
    if scored["s_acc"] is None:
        print(f"  known subtotal  {scored['s_total_excluding_accuracy']:>10.2f}"
              "   (0.3*perf + 0.2*eff, accuracy absent)")
    print("=" * 68)

    if scored["core_temp_c_peak"] is None:
        print("\nNOTE: no CPU temperature was readable. That is an ABSENCE OF "
              "MEASUREMENT,\n      not a clean thermal result. Do not report it as a pass.")

    if failures:
        print("\nHARD FAILS:", file=sys.stderr)
        for f in failures:
            print(f"  - {f}", file=sys.stderr)
        return 1

    print(f"\nwrote {run_dir}/run.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
