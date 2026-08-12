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
from run_guards import audit_archive, latency_quotable  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
RUNS = REPO / "runs"

# COMPETITION.md section 9g: the date after which VPS medians may stand in for a physical
# telemetry run, under the central-estimate rule, with spread documented.
PHYSICAL_DEADLINE = date(2026, 8, 18)


def newest(pattern: str, filename: str):
    matches = sorted(RUNS.glob(f"{pattern}/{filename}"), key=lambda p: p.stat().st_mtime)
    return matches[-1] if matches else None


def _load(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def gather(today: date | None = None) -> dict:
    today = today or date.today()
    figures: dict[str, dict] = {}
    blocked: list[dict] = []

    # ---- accuracy (internal proxy, always quotable but always labelled) ----
    path = newest("*_lmeval*", "lmeval.json")
    if path:
        data = _load(path) or {}
        figures["accuracy_proxy"] = {
            "source": str(path.parent.name),
            "label": "INTERNAL PROXY. S_acc is judge-scored; this never enters as accuracy.",
            "tasks": data.get("tasks"),
            "limit": data.get("limit"),
            "results": {k: v.get("mean_score") for k, v in (data.get("results") or {}).items()
                        if isinstance(v, dict)},
        }
    else:
        blocked.append({"figure": "accuracy_proxy", "reason": "no lmeval run archived"})

    # ---- composite / finalists ----
    path = newest("*_composite*", "composite.json")
    if path:
        data = _load(path) or {}
        figures["composite"] = {
            "source": path.parent.name,
            "finalists": data.get("finalists"),
            "tie_rule": data.get("tie_rule"),
            "label": "INTERNAL PROXY ranking. Bands, not points.",
        }
    else:
        blocked.append({"figure": "composite", "reason": "composite not yet built"})

    # ---- latency: consumer-side refusal ----
    archive = audit_archive()
    if archive["quotable_latency"]:
        name = archive["quotable_latency"][-1]
        record = _load(RUNS / name / "chat.json") or {}
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
    path = newest("*_bench*", "bench.json")
    physical = None   # a physical-host telemetry run, when one exists
    for candidate in sorted(RUNS.glob("*/run.json")):
        data = _load(candidate) or {}
        if (data.get("host_class") == "physical") and data.get("status") == "ok":
            physical = candidate
    if physical:
        figures["telemetry"] = {
            "source": physical.parent.name,
            "basis": "physical machine, official profiler, no flags of ours",
            "fallback_invoked": False,
        }
    elif today >= PHYSICAL_DEADLINE and path:
        data = _load(path) or {}
        figures["telemetry"] = {
            "source": path.parent.name,
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


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

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
