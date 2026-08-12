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
import run_guards  # noqa: E402
from run_guards import (  # noqa: E402
    Absent,
    UnquotableFigure,
    assert_latency_quotable,
    audit_archive,
)

REPO = Path(__file__).resolve().parents[1]
MANIFEST = REPO / "competition" / "candidates.yaml"

TPS_REFERENCE = 15.0
RAM_LIMIT_GB = 7.0

W_ACC, W_PERF, W_EFF = 0.50, 0.30, 0.20


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


def perf_band(bench: dict, candidate: str, run_id: str) -> tuple[float, float, float] | None:
    """(median, low, high) S_perf from measured throughput, or None if unmeasured.

    Returns None rather than zero for a candidate with no throughput data. An earlier
    version returned 0.0, which silently charged five candidates the full 30% weight for
    never having been benchmarked and produced a finalist set of one that was an artefact
    of missing data, not a measurement.

    The figures arrive typed, so the zero cannot come back by a different route: an
    `Absent` median refuses to be divided by the reference at all.
    """
    median = run_guards.figure(bench, "summary", candidate, "median_generation_tok_s",
                               run_id=run_id, why=f"{candidate} is not in this bench run")
    if isinstance(median, Absent):
        return None
    lo = run_guards.figure(bench, "summary", candidate, "min", run_id=run_id)
    hi = run_guards.figure(bench, "summary", candidate, "max", run_id=run_id)
    # A run that recorded a median but no min/max is a narrower claim, not a missing one.
    lo = median if isinstance(lo, Absent) else lo
    hi = median if isinstance(hi, Absent) else hi
    to_score = lambda tps: min(float(tps) / TPS_REFERENCE, 1.0) * 100
    return to_score(median), to_score(lo), to_score(hi)


def eff_score(peak_rss_mb: float) -> float:
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

    def source(explicit: Path | None, pattern: str, filename: str):
        if explicit:
            run_id, record = run_guards.record_at(explicit)
            return run_id, record, explicit
        return run_guards.newest_record(pattern, filename) if args.auto else None

    lmeval_src = source(args.lmeval, "*_lmeval*", "lmeval.json")
    bench_src = source(args.bench, "*_bench*", "bench.json")

    missing = [n for n, s in (("lmeval", lmeval_src), ("bench", bench_src)) if not s]
    if missing:
        print(f"error: no {', '.join(missing)} results found. "
              f"Run scripts/lmeval_mix.py and scripts/bench_screened.py first.",
              file=sys.stderr)
        return 2

    lmeval_id, lmeval, lmeval_path = lmeval_src
    bench_id, bench, bench_path = bench_src

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
    # Provisional unless the bench source positively declares a physical host, on the same
    # fail-closed principle as latency_quotable. A shared host cannot order candidates
    # separated by less than its own spread (COMPETITION.md section 9f-bis), so its perf
    # column is a placeholder that happens to be numeric, and the record has to say so.
    perf_host_class = bench.get("host_class") or "unstated"
    provisional = perf_host_class != "physical"

    manifest = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
    sizes = {c["id"]: c.get("file_mb") for c in manifest["candidates"]}
    rss_override = run_guards.read(args.rss) if args.rss else {}

    # Consumer-side guard, same pattern as FIDELITY_STALE: a figure that must not be
    # quoted cannot enter the table even if someone forgets why it was marked.
    latency = None
    if args.latency_from:
        _, record = run_guards.record_at(args.latency_from)
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
        band = perf_band(bench, candidate, bench_id)
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

    # A provisional table partitions; it does not order. The perf term is noise on this
    # host (section 9f-bis), so "which of these two is ahead" has no answer here, only a
    # leader-by-arithmetic that would read as a result. The selection set is emitted
    # sorted by id precisely so it cannot be mistaken for a ranking.
    selection_set = sorted(r["id"] for r in finalists)
    excluded = sorted(r["id"] for r in scored if r["id"] not in set(selection_set))
    partition = {
        "selection_set": selection_set,
        "excluded": excluded,
        "ordering_claimed": not provisional,
        "basis": (
            "band overlap with the widest band in the table. Membership is a claim; "
            "position inside the set is not, until throughput is measured on hardware "
            "that can resolve it (COMPETITION.md section 9f-bis)."
            if provisional else
            "band overlap with the leader's band, from a complete ranking"
        ),
    }

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = run_guards.new_run_dir(stamp, "composite")
    record = {
        "recorded_at": stamp,
        "label": "INTERNAL PROXY. S_acc is judge-scored; this ranks candidates only.",
        "sources": {"lmeval": str(lmeval_path), "bench": str(bench_path)},
        "source_runs": {"lmeval": lmeval_id, "bench": bench_id},
        "weights": {"accuracy": W_ACC, "throughput": W_PERF, "efficiency": W_EFF},
        "constants": {"tps_reference": TPS_REFERENCE, "ram_limit_gb": RAM_LIMIT_GB},
        "rows": scored,
        "errors": [r for r in rows if "error" in r],
        "not_ranked_missing_throughput": [r["id"] for r in incomplete],
        "ranking_complete": not incomplete,
        "bench_image": bench_image,
        "perf_host_class": perf_host_class,
        "provisional": provisional,
        "provisional_reason": (
            None if not provisional else
            f"throughput measured on a {perf_host_class} host. Section 9f-bis: this "
            f"column carries no ordering authority, and the physical sitting re-measures "
            f"it and re-forms the table (completion, not verification)."
        ),
        "partition": partition,
        "finalists": selection_set if provisional else [r["id"] for r in finalists],
        "finalist_label": (
            "provisional cluster: the set worth taking to the qualitative pass, not a "
            "ranking" if provisional else "finalist set from a complete ranking"
        ),
        "tie_rule": "composite band overlaps the leader's band",
        "latency": ("omitted: no quotable run" if latency is None
                    else latency.get("_meta", {}).get("run_dir")),
        "archive_audit": audit_archive(),
    }
    (out_dir / "composite.json").write_text(json.dumps(record, indent=2) + "\n",
                                            encoding="utf-8")

    print("INTERNAL PROXY. Bands, not points: this host resolves throughput to ~27%.\n")
    if provisional:
        print("  PARTITION, not a ranking. Rows are sorted by id inside each group: the\n"
              "  set membership is a claim, the order within it is not.\n")
    # Sorting the display by composite would present an ordering the perf term cannot
    # support. Provisional tables print alphabetically, grouped by selection membership.
    display_rows = (sorted(scored, key=lambda r: (r["id"] not in selection_set, r["id"]))
                    if provisional else scored)
    print(f"  {'candidate':30s} {'compos':>7s} {'band':>16s} {'acc':>7s} {'perf':>6s} {'eff':>6s}")
    for r in display_rows:
        band = f"[{r['composite_band'][0]:.1f},{r['composite_band'][1]:.1f}]"
        if provisional:
            mark = " <- selection set" if r["id"] in selection_set else ""
        else:
            mark = " <- finalist" if r["id"] in record["finalists"] else ""
        print(f"  {r['id']:30s} {r['composite']:7.2f} {band:>16s} "
              f"{r['accuracy_proxy']:7.2f} {r['s_perf']:6.2f} {r['s_eff']:6.2f}{mark}")
    for r in record["errors"]:
        print(f"  {r['id']:30s} {'ERROR':>7s}  {r['error'][:44]}")

    archive = audit_archive()
    if not archive["quotable_latency"]:
        print("\n  latency: no quotable run in the archive, so no latency column is "
              "shown.\n           Expected until the O-12 physical sitting (section 9g).")

    if provisional:
        print(f"\n  PROVISIONAL: throughput came from a {perf_host_class} host, which "
              f"cannot order\n  candidates closer together than its own spread. The "
              f"physical sitting re-measures\n  perf and re-forms this table (section "
              f"9f-bis: completion, not verification).")

    print(f"\n  {'provisional cluster' if provisional else 'finalist set'} "
          f"({len(finalists)}): {', '.join(record['finalists'])}")
    print("  These go to the three-arm qualitative pass, which discriminates better than")
    print("  any of these numbers for a submission judged by conversation.")
    print(f"\nwrote {out_dir}/composite.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
