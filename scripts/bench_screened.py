#!/usr/bin/env python3
"""BUILD TIME. Steal-screened, interleaved throughput measurement for RANKING only.

WHY THIS EXISTS
---------------
Two runs of the same model, benchmark and image on this host disagreed by 2.5x
(1.82 vs 4.50 tok/s). On a shared virtualised host `--cpus=4` is a scheduling quota, not
pinned cores, so a noisy neighbour silently halves throughput and nothing in the profiler
notices.

That matters beyond the score. Gate 2 diffs our submitted telemetry against the audit and
**fails beyond 50% in either direction** (verified against `comparator.py`; the check uses
abs() on a delta normalised by the SUBMITTED value, so under-claiming actually fails
sooner than over-claiming).

TWO USES, KEPT APART (COMPETITION.md section 9e)
------------------------------------------------
  RANKING   comparing candidates against each other. This script. A VPS is fine, because
            steal screening plus interleaving plus medians make the COMPARISON sound even
            when absolute values are depressed.
  TELEMETRY the single figure in submission.json. This script must NOT produce it. That
            comes from a physical machine near the Standard Laptop spec, running the
            official image with the same caps.

HOW SCREENING WORKS
-------------------
CPU steal is read from /proc/stat field 8 (cumulative jiffies stolen by the hypervisor),
sampled either side of each repetition. A repetition whose steal fraction exceeds the
threshold is DISCARDED, not averaged in: a contended run is not a noisy measurement of
the truth, it is a measurement of a different machine.

Candidates are INTERLEAVED (A,B,C,A,B,C, ...) rather than run in blocks, so a slow period
lands across all candidates instead of penalising whichever happened to run during it.

Usage:
    python3 scripts/bench_screened.py --candidates qwen3.5-0.8b-q4_k_m,llama-3.2-1b-instruct-q4_k_m
    python3 scripts/bench_screened.py --candidates all --reps 5 --max-steal 1.0
"""
from __future__ import annotations

import argparse
import json
import statistics
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
IMAGE = "adtc-profiler:latest"
AUDIT_MEMORY = "7.5g"
AUDIT_CPUS = "4"


def read_cpu_times() -> tuple[int, int]:
    """(total_jiffies, steal_jiffies) from /proc/stat's aggregate cpu line."""
    with open("/proc/stat", encoding="utf-8") as fh:
        for line in fh:
            if line.startswith("cpu "):
                fields = [int(x) for x in line.split()[1:]]
                # user nice system idle iowait irq softirq steal guest guest_nice
                steal = fields[7] if len(fields) > 7 else 0
                return sum(fields), steal
    raise RuntimeError("no aggregate cpu line in /proc/stat")


def steal_percent(before: tuple[int, int], after: tuple[int, int]) -> float:
    total_delta = after[0] - before[0]
    steal_delta = after[1] - before[1]
    if total_delta <= 0:
        return 0.0
    return steal_delta / total_delta * 100.0


def load_candidates(spec: str) -> list[str]:
    manifest = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
    known = [c["id"] for c in manifest["candidates"]]
    if spec == "all":
        return known
    wanted = [s.strip() for s in spec.split(",") if s.strip()]
    unknown = [w for w in wanted if w not in known and w != manifest["smoke"]["id"]]
    if unknown:
        raise SystemExit(f"unknown candidate(s): {unknown}. Known: {known}")
    return wanted


def bench_once(candidate: str, image: str = IMAGE) -> dict:
    """One llama-bench repetition, with steal sampled either side."""
    model = BAKEOFF / f"{candidate}.gguf"
    if not model.exists():
        return {"error": f"{model} not found"}

    before = read_cpu_times()
    started = time.time()
    proc = subprocess.run([
        "docker", "run", "--rm",
        f"--memory={AUDIT_MEMORY}", f"--memory-swap={AUDIT_MEMORY}",
        f"--cpus={AUDIT_CPUS}",
        "-v", f"{BAKEOFF}:/m:ro",
        "--entrypoint", "llama-bench", image,
        "-m", f"/m/{candidate}.gguf", "-p", "512", "-n", "128", "-ngl", "0",
        "--output", "json",
    ], capture_output=True, text=True)
    elapsed = time.time() - started
    after = read_cpu_times()
    steal = steal_percent(before, after)

    if proc.returncode != 0:
        return {"error": f"llama-bench exit {proc.returncode}", "steal_pct": steal,
                "stderr": proc.stderr[-400:]}
    try:
        rows = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        return {"error": f"unparseable output: {exc}", "steal_pct": steal}

    tg = next((r for r in rows if r.get("n_gen", 0) > 0), None)
    pp = next((r for r in rows if r.get("n_gen", 0) == 0 and r.get("n_prompt", 0) > 0), None)
    return {
        "generation_tok_s": float(tg["avg_ts"]) if tg else None,
        "prompt_tok_s": float(pp["avg_ts"]) if pp else None,
        "steal_pct": round(steal, 3),
        "wall_seconds": round(elapsed, 1),
    }


def summarise(reps: list[dict], max_steal: float) -> dict:
    kept = [r for r in reps
            if not r.get("error") and r.get("generation_tok_s")
            and r["steal_pct"] <= max_steal]
    discarded = [r for r in reps if r not in kept]
    values = sorted(r["generation_tok_s"] for r in kept)
    if not values:
        return {"kept": 0, "discarded": len(discarded), "median": None,
                "reason": "every repetition was discarded or failed"}
    median = statistics.median(values)
    spread = (max(values) - min(values)) / median * 100 if median else None
    return {
        "kept": len(kept),
        "discarded": len(discarded),
        "median_generation_tok_s": round(median, 3),
        "min": round(min(values), 3),
        "max": round(max(values), 3),
        "spread_pct_of_median": round(spread, 1) if spread is not None else None,
        "max_steal_seen": round(max((r.get("steal_pct", 0) for r in reps), default=0), 3),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--candidates", required=True, help="comma-separated ids, or 'all'")
    ap.add_argument("--reps", type=int, default=3)
    ap.add_argument("--max-steal", type=float, default=1.0,
                    help="discard any repetition whose CPU steal exceeds this percent")
    ap.add_argument("--tag", default="")
    ap.add_argument("--image", default=IMAGE,
                    help="adtc-profiler:latest (submittable protocol) or adtc-native:latest "
                         "(SIMD comparison only, never submitted)")
    args = ap.parse_args()

    candidates = load_candidates(args.candidates)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    suffix = f"_{args.tag}" if args.tag else ""
    out_dir = RUNS / f"{stamp}_bench{suffix}"
    out_dir.mkdir(parents=True, exist_ok=True)

    baseline = read_cpu_times()
    time.sleep(1)
    idle_steal = steal_percent(baseline, read_cpu_times())
    print(f"candidates: {', '.join(candidates)}")
    print(f"reps:       {args.reps} (interleaved)")
    print(f"screening:  discard repetitions above {args.max_steal}% CPU steal")
    print(f"image:      {args.image}")
    print(f"idle steal: {idle_steal:.3f}%")
    print("\nFOR RANKING ONLY. The submitted telemetry figure must come from a physical")
    print("machine near the Standard Laptop spec (COMPETITION.md section 9e).\n")

    results: dict[str, list[dict]] = {c: [] for c in candidates}
    # Interleaved: a slow period hits every candidate rather than one.
    for rep in range(1, args.reps + 1):
        for candidate in candidates:
            print(f"  rep {rep}/{args.reps}  {candidate} … ", end="", flush=True)
            row = bench_once(candidate, args.image)
            row["rep"] = rep
            results[candidate].append(row)
            if row.get("error"):
                print(f"ERROR {row['error']}")
            else:
                verdict = "keep" if row["steal_pct"] <= args.max_steal else "DISCARD"
                print(f"{row['generation_tok_s']:.2f} tok/s  "
                      f"steal {row['steal_pct']:.2f}%  [{verdict}]")

    summary = {c: summarise(rows, args.max_steal) for c, rows in results.items()}
    record = {
        "recorded_at": stamp,
        "purpose": "RANKING ONLY. Not submittable telemetry.",
        "image": args.image,
        "constraints": {"memory": AUDIT_MEMORY, "cpus": AUDIT_CPUS},
        "reps": args.reps,
        "max_steal_pct": args.max_steal,
        "idle_steal_pct": round(idle_steal, 3),
        "host_note": "shared virtualised host; --cpus is a quota, not pinned cores",
        "raw": results,
        "summary": summary,
    }
    (out_dir / "bench.json").write_text(json.dumps(record, indent=2) + "\n",
                                        encoding="utf-8")

    print("\n" + "=" * 78)
    print(f"  {'candidate':34s} {'median':>9s} {'min':>8s} {'max':>8s} "
          f"{'spread':>8s} {'kept':>6s}")
    for candidate in candidates:
        s = summary[candidate]
        if s.get("median_generation_tok_s") is None:
            print(f"  {candidate:34s} {'NO DATA':>9s}  ({s.get('reason', '')})")
            continue
        print(f"  {candidate:34s} {s['median_generation_tok_s']:9.2f} "
              f"{s['min']:8.2f} {s['max']:8.2f} "
              f"{str(s['spread_pct_of_median']) + '%':>8s} "
              f"{s['kept']}/{s['kept'] + s['discarded']:>3}")
    print("=" * 78)

    wide = [c for c in candidates
            if (summary[c].get("spread_pct_of_median") or 0) > 25]
    if wide:
        print(f"\nWARNING: spread above 25% for {wide}. The ranking between candidates")
        print("that close together is not resolved. Add repetitions or a quieter host.")

    print(f"\nwrote {out_dir}/bench.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
