#!/usr/bin/env python3
"""BUILD TIME. Assemble the figures destined for REPORT.md, refusing unquotable ones.

WHY A BUILDER RATHER THAN TYPING NUMBERS IN
-------------------------------------------
REPORT.md carries `[PENDING ...]` markers where measurements go. Filling those by hand is
how a stale figure gets in: the number is copied, the caveat is not, and six sections
later nobody can tell which run produced it.

This walks `runs/` instead, applies the same consumer-side guards `composite.py` uses, and
emits only figures that are permitted to be quoted, each with its run id. Anything blocked
is reported as blocked, with the reason, so an absence is visible rather than silent.

    latency   requires a run stamped latency_quotable (O-12 physical sitting)
    telemetry requires an official-image profiler run; VPS medians are permitted only
              under the section 9g fallback, and are then labelled as such
    accuracy  internal proxy, always labelled, never a submitted number

Usage:
    python3 scripts/report_figures.py            # human summary
    python3 scripts/report_figures.py --json     # machine-readable
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_guards  # noqa: E402
from run_guards import Absent, audit_archive  # noqa: E402

REPO = Path(__file__).resolve().parents[1]

# COMPETITION.md section 9g: the date after which VPS medians may stand in for a physical
# telemetry run, under the central-estimate rule, with spread documented.
PHYSICAL_DEADLINE = date(2026, 8, 18)


def gather(today: date | None = None) -> dict:
    today = today or date.today()
    figures: dict[str, dict] = {}
    blocked: list[dict] = []

    # ---- accuracy (internal proxy, always quotable but always labelled) ----
    found = run_guards.newest_record("*_lmeval*", "lmeval.json")
    if found:
        run_id, data, _ = found
        figures["accuracy_proxy"] = {
            "source": run_id,
            "label": "INTERNAL PROXY. S_acc is judge-scored; this never enters as accuracy.",
            "tasks": data.get("tasks"),
            "limit": data.get("limit"),
            "results": {k: v.get("mean_score") for k, v in (data.get("results") or {}).items()
                        if isinstance(v, dict)},
        }
    else:
        blocked.append({"figure": "accuracy_proxy", "reason": "no lmeval run archived"})

    # ---- composite / finalists ----
    #
    # A composite formed while some candidate has no throughput data is not a ranking of
    # six candidates, it is a ranking of the ones that happened to be measured. Its
    # finalist set reads exactly like a real one, so it is refused here rather than
    # labelled: the first finalist set this project produced named a single model only
    # because five candidates were absent from the table.
    found = run_guards.newest_record("*_composite*", "composite.json")
    if found:
        run_id, data, _ = found
        unranked = data.get("not_ranked_missing_throughput") or []
        if data.get("ranking_complete") is True and not unranked:
            # Complete is not the same as final. A table whose throughput came from a
            # shared host is provisional by construction (COMPETITION.md section 9f-bis),
            # and the flag travels with the figure so nobody has to remember why.
            provisional = data.get("provisional", True)
            partition = data.get("partition") or {}
            figures["composite"] = {
                "source": run_id,
                # A provisional table yields a set, not an order. Sorting by id here is
                # not cosmetic: an ordered list is read as a ranking by whoever quotes it.
                "selection_set": sorted(partition.get("selection_set")
                                        or data.get("finalists") or []),
                "excluded": sorted(partition.get("excluded") or []),
                "ordering_claimed": partition.get("ordering_claimed", not provisional),
                "finalists": data.get("finalists"),
                "tie_rule": data.get("tie_rule"),
                "provisional": provisional,
                "perf_host_class": data.get("perf_host_class", "unstated"),
                "label": (
                    "PROVISIONAL cluster, INTERNAL PROXY. Throughput from a "
                    f"{data.get('perf_host_class', 'unstated')} host orders nothing; the "
                    "physical sitting re-measures perf and re-forms the table."
                    if provisional else
                    "INTERNAL PROXY ranking, complete. Bands, not points."
                ),
            }
        else:
            blocked.append({
                "figure": "composite",
                "reason": (
                    f"{run_id} is incomplete: "
                    f"{len(unranked)} candidate(s) have no throughput data "
                    f"({', '.join(unranked) or 'unlisted'}). A finalist set drawn from a "
                    "partial table is an artefact of what was measured. Re-run "
                    "scripts/composite.py --auto once the bench sweep covers every "
                    "candidate."
                ),
                "unranked": unranked,
            })
    else:
        blocked.append({"figure": "composite", "reason": "composite not yet built"})

    # ---- latency: consumer-side refusal ----
    archive = audit_archive()
    if archive["quotable_latency"]:
        name = archive["quotable_latency"][-1]
        record = run_guards.record_in(name, "chat.json")
        times = [t.get("seconds") for t in record.get("turns", []) if t.get("seconds")]
        figures["judge_latency"] = {
            "source": name,
            "median_seconds": sorted(times)[len(times) // 2] if times else None,
            "host_class": (record.get("_meta") or {}).get("host_class"),
        }
    else:
        blocked.append({
            "figure": "judge_latency",
            "reason": (
                "no run stamped latency_quotable. Shared-host and FIDELITY_STALE runs are "
                "refused by design; latency requires the O-12 physical sitting "
                "(COMPETITION.md section 9g)."
            ),
            "stale_runs": len(archive["fidelity_stale"]),
            "shared_runs": len(archive["shared_host_not_quotable"]),
        })

    # ---- submitted telemetry, with the dated fallback ----
    bench_found = run_guards.newest_record("*_bench*", "bench.json")
    physical = None   # a physical-host telemetry run, when one exists
    for run_id, data in run_guards.all_records("*", "run.json"):
        if (data.get("host_class") == "physical") and data.get("status") == "ok":
            physical = run_id
    if physical:
        figures["telemetry"] = {
            "source": physical,
            "basis": "physical machine, official profiler, no flags of ours",
            "fallback_invoked": False,
        }
    elif today >= PHYSICAL_DEADLINE and bench_found:
        run_id, data, _ = bench_found
        figures["telemetry"] = {
            "source": run_id,
            "basis": "VPS screened medians under the section 9g fallback",
            "fallback_invoked": True,
            "summary": data.get("summary"),
            "label": (
                "FALLBACK. No physical machine was available by "
                f"{PHYSICAL_DEADLINE.isoformat()}. Submitted under the central-estimate "
                "rule with measured spread documented; not a claim about the audit box."
            ),
        }
    else:
        blocked.append({
            "figure": "telemetry",
            "reason": (
                f"no physical-host profiler run, and the section 9g fallback does not "
                f"open until {PHYSICAL_DEADLINE.isoformat()} "
                f"(today {today.isoformat()})."
            ),
        })

    return {
        "generated": today.isoformat(),
        "figures": figures,
        "blocked": blocked,
        "archive_audit": archive,
        "physical_deadline": PHYSICAL_DEADLINE.isoformat(),
    }


def numeric_manifest(today: date | None = None) -> dict:
    """Every numeric value REPORT.md is permitted to state, with its provenance.

    THE RULE (COMPETITION.md section 9h): a measured figure enters REPORT.md only if it
    appears here. Typing a number by hand is how a value arrives without its caveat, and
    how nobody can tell six sections later which run produced it.

    Values are keyed as STRINGS exactly as they should appear in prose, because the check
    is a textual one against the document.
    """
    report = gather(today)
    manifest: dict[str, str] = {}

    def add(fig, provenance: str, places: tuple[int, ...] = (0, 1, 2)) -> None:
        """Enter one measurement into the manifest. An `Absent` enters nothing.

        Absence is skipped here rather than defaulted, so a field a run never recorded
        simply cannot be quoted. The typed figure makes that the only available
        behaviour: there is no value to write.
        """
        if isinstance(fig, Absent):
            return
        value = float(fig)
        for digits in places:
            manifest[f"{value:.{digits}f}".rstrip("0").rstrip(".")
                     if digits else f"{value:.0f}"] = provenance
            manifest[f"{value:.{digits}f}"] = provenance

    # Accuracy proxy, per candidate, from EVERY archived sweep rather than only the newest.
    #
    # A candidate can legitimately be quoted from an older run: the pre-registered cluster
    # rule re-scores tied candidates only, so an untied candidate's last measurement stays
    # its current one and belongs in a footnote at its own limit. Keying provenance by run
    # id is what makes that safe, and matches how bench runs are already handled. gather()
    # still surfaces the newest sweep as the headline figure.
    for run_id, data in run_guards.all_records("*_lmeval*", "lmeval.json"):
        results = {k: v.get("mean_score") for k, v in (data.get("results") or {}).items()
                   if isinstance(v, dict)}
        for candidate in results:
            mean = run_guards.figure(results, candidate, run_id=run_id)
            if isinstance(mean, Absent):
                continue
            provenance = f"accuracy_proxy/{candidate}/{run_id}"
            add(run_guards.Measurement(float(mean) * 100, candidate, run_id), provenance)
            add(mean, provenance)

    # Throughput, from every archived screened bench run.
    for run_id, data in run_guards.all_records("*_bench*", "bench.json"):
        origin = f"bench/{run_id}"
        for candidate in (data.get("summary") or {}):
            for key in ("median_generation_tok_s", "min", "max", "spread_pct_of_median"):
                add(run_guards.figure(data, "summary", candidate, key, run_id=run_id),
                    f"{origin}/{candidate}/{key}")

    # Profiler telemetry from archived runs.
    for run_id, data in run_guards.all_records("*", "run.json"):
        origin = f"profiler/{run_id}"
        for key in ("tokens_per_second", "peak_rss_mb", "peak_rss_gb", "s_perf", "s_eff"):
            add(run_guards.figure(data, "score", key, run_id=run_id), f"{origin}/{key}")

    # O-09 spot check: native versus in-image accuracy, and what each cost in wall clock.
    for run_id, data in run_guards.all_records("*_spotcheck_*", "spotcheck.json"):
        origin = f"spotcheck/{run_id}"
        for section in ("official", "native"):
            for key in ("wall_seconds", "eval_seconds", "load_seconds", "mean_score"):
                add(run_guards.figure(data, section, key, run_id=run_id),
                    f"{origin}/{section}/{key}")
        add(run_guards.figure(data, "eval_speedup_native", run_id=run_id),
            f"{origin}/eval_speedup_native")

    # SIMD comparison.
    for run_id, data in run_guards.all_records("*_simd_*", "simd_summary.json"):
        origin = f"simd/{run_id}"
        for section in ("official_image", "native_avx2_image"):
            for key in (data.get(section) or {}):
                add(run_guards.figure(data, section, key, run_id=run_id),
                    f"{origin}/{section}/{key}")
        for key in ("speedup_generation", "speedup_prompt"):
            add(run_guards.figure(data, key, run_id=run_id), f"{origin}/{key}")

    return {"manifest": manifest, "report": report}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--manifest", action="store_true",
                    help="emit every number REPORT.md may state, with provenance")
    args = ap.parse_args()

    if args.manifest:
        data = numeric_manifest()
        print(json.dumps(data["manifest"], indent=2, sort_keys=True))
        return 0

    report = gather()
    if args.json:
        print(json.dumps(report, indent=2))
        return 0

    print(f"report figures as of {report['generated']}\n")
    print("AVAILABLE:")
    for name, value in report["figures"].items():
        label = value.get("label", "")
        print(f"  {name:18s} <- {value.get('source')}")
        if label:
            print(f"  {'':18s}    {label[:96]}")
    if not report["figures"]:
        print("  (none)")

    print("\nBLOCKED:")
    for item in report["blocked"]:
        print(f"  {item['figure']:18s} {item['reason']}")
    if not report["blocked"]:
        print("  (none)")

    print(f"\nphysical-machine deadline: {report['physical_deadline']} "
          "(section 9g fallback opens after this)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
