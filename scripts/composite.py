#!/usr/bin/env python3
"""BUILD TIME. Build the composite ranking table with propagated uncertainty.

THE POINT OF THE UNCERTAINTY
----------------------------
This host cannot reproduce its own throughput to better than ~27% (COMPETITION.md
section 9e). A composite that reports a single number per candidate would imply an
ordering the measurements do not support, and the first thing anyone would do with it is
pick a winner by the third decimal place.

So every candidate gets a BAND, not a point:

  accuracy    binomial sampling error over the mix, se = sqrt(p(1-p)/n) per task,
              combined across tasks. An internal proxy of unknown fidelity to S_acc, so
              this band understates the true uncertainty and the report says so.
  throughput  the measured min/max across screened repetitions, which is the honest
              statement of what this host can resolve.
  efficiency  peak RSS varies far less than throughput; treated as a point unless
              repetitions are supplied.

TIES ARE THE OUTPUT, NOT A PROBLEM
----------------------------------
Candidates whose bands overlap the leader's band are TIED. The tie cluster is the
finalist set that goes forward to the three-arm qualitative pass, which is a better
discriminator than any of these numbers for a submission judged by conversation.

O-13 (warm-up versus bandwidth contention) adjusts band WIDTHS. It never blocks this
table: narrower bands may shrink the tie cluster later, and that is a refinement of the
finalist set rather than a precondition for having one.

Usage:
    python3 scripts/composite.py --lmeval runs/<id>/lmeval.json --bench runs/<id>/bench.json
    python3 scripts/composite.py --auto      # newest of each
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_guards import UnquotableFigure, assert_latency_quotable, audit_archive  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
RUNS = REPO / "runs"
MANIFEST = REPO / "competition" / "candidates.yaml"

TPS_REFERENCE = 15.0
RAM_LIMIT_GB = 7.0

W_ACC, W_PERF, W_EFF = 0.50, 0.30, 0.20


def newest(pattern: str, filename: str) -> Path | None:
    matches = sorted(RUNS.glob(f"{pattern}/{filename}"), key=lambda p: p.stat().st_mtime)
    return matches[-1] if matches else None


def accuracy_band(tasks: dict) -> tuple[float, float, float]:
    """(mean, low, high) as percentages, from binomial sampling error per task."""
    scores, variances = [], []
    for row in tasks.values():
        if "score" not in row:
            continue
        p = float(row["score"])
        n = max(int(row.get("samples", 1)), 1)
        scores.append(p)
        variances.append(p * (1 - p) / n)
    if not scores:
        return 0.0, 0.0, 0.0
    mean = sum(scores) / len(scores)
    # Mean of k independent task scores: variance divides by k^2.
    se = math.sqrt(sum(variances)) / len(scores)
    return mean * 100, max(0.0, (mean - 1.96 * se)) * 100, min(1.0, (mean + 1.96 * se)) * 100


OFFICIAL_IMAGE = "adtc-profiler:latest"


def perf_band(bench_summary: dict) -> tuple[float, float, float] | None:
    """(median, low, high) S_perf from measured throughput min/max, or None if unmeasured.

    Returns None rather than zero for a candidate with no throughput data. An earlier
    version returned 0.0, which silently charged five candidates the full 30% weight for
    never having been benchmarked and produced a finalist set of one that was an artefact
    of missing data, not a measurement.
    """
    median = bench_summary.get("median_generation_tok_s")
    if median is None:
        return None
    lo = bench_summary.get("min", median)
    hi = bench_summary.get("max", median)
    to_score = lambda tps: min(tps / TPS_REFERENCE, 1.0) * 100
    return to_score(median), to_score(lo), to_score(hi)


def eff_score(peak_rss_mb: float | None) -> float:
    if not peak_rss_mb:
        return 0.0
    return max(0.0, (RAM_LIMIT_GB - peak_rss_mb / 1024.0) / RAM_LIMIT_GB) * 100


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lmeval", type=Path)
    ap.add_argument("--bench", type=Path)
    ap.add_argument("--auto", action="store_true")
    ap.add_argument("--rss", type=Path, help="optional JSON of {candidate: peak_rss_mb}")
    ap.add_argument("--allow-non-official", action="store_true",
                    help="permit a bench file from a non-official image. Only for a "
                         "labelled comparison, never for a ranking that informs the "
                         "submission.")
    ap.add_argument("--latency-from", type=Path,
                    help="optional chat.json to annotate rows with judge-real latency. "
                         "REFUSED unless the run is stamped latency_quotable.")
    args = ap.parse_args()

    lmeval_path = args.lmeval or (newest("*_lmeval*", "lmeval.json") if args.auto else None)
    bench_path = args.bench or (newest("*_bench*", "bench.json") if args.auto else None)

    missing = [n for n, p in (("lmeval", lmeval_path), ("bench", bench_path)) if not p]
    if missing:
        print(f"error: no {', '.join(missing)} results found. "
              f"Run scripts/lmeval_mix.py and scripts/bench_screened.py first.",
              file=sys.stderr)
        return 2

    lmeval = json.loads(lmeval_path.read_text(encoding="utf-8"))
    bench = json.loads(bench_path.read_text(encoding="utf-8"))

    # Provenance guard. --auto takes the newest bench file, which once selected the
    # never-submitted native AVX2 build. A ranking built on a build we have promised not
    # to submit is not a ranking of the thing we are submitting.
    bench_image = bench.get("image")
    if bench_image != OFFICIAL_IMAGE and not args.allow_non_official:
        print(f"error: {bench_path} was produced by {bench_image!r}, not "
              f"{OFFICIAL_IMAGE!r}.\n"
              f"  Throughput for ranking must come from the official image "
              f"(COMPETITION.md section 11).\n"
              f"  Pass --allow-non-official only for an explicitly labelled comparison.",
              file=sys.stderr)
        return 2
    manifest = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
    sizes = {c["id"]: c.get("file_mb") for c in manifest["candidates"]}
    rss_override = json.loads(args.rss.read_text()) if args.rss else {}

    # Consumer-side guard, same pattern as FIDELITY_STALE: a figure that must not be
    # quoted cannot enter the table even if someone forgets why it was marked.
    latency = None
    if args.latency_from:
        record = json.loads(args.latency_from.read_text(encoding="utf-8"))
        try:
            assert_latency_quotable(record, str(args.latency_from))
        except UnquotableFigure as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        latency = record

    rows = []
    for candidate, acc_row in (lmeval.get("results") or {}).items():
        if acc_row.get("error"):
            rows.append({"id": candidate, "error": acc_row["error"]})
            continue
        acc, acc_lo, acc_hi = accuracy_band(acc_row.get("tasks", {}))
        band = perf_band((bench.get("summary") or {}).get(candidate, {}))
        if band is None:
            rows.append({
                "id": candidate,
                "accuracy_proxy": round(acc, 2),
                "incomplete": "no throughput measurement; not ranked",
            })
            continue
        perf, perf_lo, perf_hi = band

        # Without a measured RSS, approximate from file size: weights dominate resident
        # set for a mmap'd GGUF. Flagged as an estimate in the output.
        measured_rss = rss_override.get(candidate)
        rss = measured_rss if measured_rss else (sizes.get(candidate) or 0) * 1.35
        eff = eff_score(rss)

        rows.append({
            "id": candidate,
            "accuracy_proxy": round(acc, 2),
            "accuracy_band": [round(acc_lo, 2), round(acc_hi, 2)],
            "s_perf": round(perf, 2),
            "s_perf_band": [round(perf_lo, 2), round(perf_hi, 2)],
            "s_eff": round(eff, 2),
            "rss_source": "measured" if measured_rss else "estimate from file size x1.35",
            "composite": round(W_ACC * acc + W_PERF * perf + W_EFF * eff, 2),
            "composite_band": [
                round(W_ACC * acc_lo + W_PERF * perf_lo + W_EFF * eff, 2),
                round(W_ACC * acc_hi + W_PERF * perf_hi + W_EFF * eff, 2),
            ],
        })

    scored = [r for r in rows if "composite" in r]
    incomplete = [r for r in rows if "incomplete" in r]
    if not scored:
        print("error: no candidate produced a composite", file=sys.stderr)
        if incomplete:
            print(f"  {len(incomplete)} candidate(s) lack throughput data: "
                  f"{', '.join(r['id'] for r in incomplete)}", file=sys.stderr)
            print("  Run: make bench CANDIDATE=all REPS=3", file=sys.stderr)
        return 1
    if incomplete:
        print(f"WARNING: {len(incomplete)} of {len(rows)} candidates are NOT RANKED for "
              f"want of throughput data:", file=sys.stderr)
        for row in incomplete:
            print(f"  {row['id']}", file=sys.stderr)
        print("  The tie cluster below is drawn from the ranked subset only and is "
              "provisional until they are measured.\n", file=sys.stderr)
    scored.sort(key=lambda r: r["composite"], reverse=True)

    # Tie rule: overlap with the leader's band. Not "within X points", which would be an
    # arbitrary threshold; band overlap is the measurements speaking for themselves.
    leader = scored[0]
    finalists = [r for r in scored if r["composite_band"][1] >= leader["composite_band"][0]]

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = RUNS / f"{stamp}_composite"
    out_dir.mkdir(parents=True, exist_ok=True)
    record = {
        "recorded_at": stamp,
        "label": "INTERNAL PROXY. S_acc is judge-scored; this ranks candidates only.",
        "sources": {"lmeval": str(lmeval_path), "bench": str(bench_path)},
        "weights": {"accuracy": W_ACC, "throughput": W_PERF, "efficiency": W_EFF},
        "constants": {"tps_reference": TPS_REFERENCE, "ram_limit_gb": RAM_LIMIT_GB},
        "rows": scored,
        "errors": [r for r in rows if "error" in r],
        "not_ranked_missing_throughput": [r["id"] for r in incomplete],
        "ranking_complete": not incomplete,
        "bench_image": bench_image,
        "finalists": [r["id"] for r in finalists],
        "tie_rule": "composite band overlaps the leader's band",
        "latency": ("omitted: no quotable run" if latency is None
                    else latency.get("_meta", {}).get("run_dir")),
        "archive_audit": audit_archive(),
    }
    (out_dir / "composite.json").write_text(json.dumps(record, indent=2) + "\n",
                                            encoding="utf-8")

    print("INTERNAL PROXY. Bands, not points: this host resolves throughput to ~27%.\n")
    print(f"  {'candidate':30s} {'compos':>7s} {'band':>16s} {'acc':>7s} {'perf':>6s} {'eff':>6s}")
    for r in scored:
        band = f"[{r['composite_band'][0]:.1f},{r['composite_band'][1]:.1f}]"
        mark = " <- finalist" if r["id"] in record["finalists"] else ""
        print(f"  {r['id']:30s} {r['composite']:7.2f} {band:>16s} "
              f"{r['accuracy_proxy']:7.2f} {r['s_perf']:6.2f} {r['s_eff']:6.2f}{mark}")
    for r in record["errors"]:
        print(f"  {r['id']:30s} {'ERROR':>7s}  {r['error'][:44]}")

    archive = audit_archive()
    if not archive["quotable_latency"]:
        print("\n  latency: no quotable run in the archive, so no latency column is "
              "shown.\n           Expected until the O-12 physical sitting (section 9g).")

    print(f"\n  finalist set ({len(finalists)}): {', '.join(record['finalists'])}")
    print("  These go to the three-arm qualitative pass, which discriminates better than")
    print("  any of these numbers for a submission judged by conversation.")
    print(f"\nwrote {out_dir}/composite.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
