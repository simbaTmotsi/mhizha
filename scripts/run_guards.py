#!/usr/bin/env python3
"""BUILD TIME. Consumer-side guards on archived run records.

WHY CONSUMER-SIDE
-----------------
Producers already stamp their output: chat runs carry `latency_quotable`, superseded runs
carry `FIDELITY_STALE.txt`. Stamping alone is only half a control, because it relies on
whoever reads the archive months later noticing the stamp. These guards put the check at
the point of USE, so a figure that must not be quoted cannot reach a table or a report
even if someone forgets why it was marked.

The pattern is the same in both directions:

    stamp at production   -> the artefact knows its own provenance
    refuse at consumption -> nothing unstamped can be presented as evidence

Both `composite.py` and `report_figures.py` import from here rather than re-implementing,
so there is exactly one definition of "may this number be quoted".
"""
from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
RUNS = REPO / "runs"

STALE_MARKER = "FIDELITY_STALE.txt"


class UnquotableFigure(RuntimeError):
    """A figure was requested from a run that is not permitted to supply it."""


def is_stale(run_dir: Path) -> bool:
    return (run_dir / STALE_MARKER).exists()


def latency_quotable(record: dict) -> bool:
    """True only when the producer positively asserted it.

    Absence is treated as NOT quotable. Every run predating the stamp was measured under
    the `-t 4` invocation, so defaulting to permissive would admit exactly the figures the
    stamp exists to exclude.
    """
    meta = record.get("_meta") or {}
    return meta.get("latency_quotable") is True


def assert_latency_quotable(record: dict, source: str) -> None:
    if latency_quotable(record):
        return
    meta = record.get("_meta") or {}
    raise UnquotableFigure(
        f"refusing a latency figure from {source}.\n"
        f"  latency_quotable: {meta.get('latency_quotable')!r} "
        f"(host_class: {meta.get('host_class')!r})\n"
        f"  Latency is quotable only from a run recorded with --host-class physical.\n"
        f"  A shared VPS is not the judges' topology and showed 27.8% run-to-run spread "
        f"on a fixed workload (COMPETITION.md sections 9e and 9g).\n"
        f"  Re-run the probe on the O-12 machine, or omit the figure."
    )


def quotable_chat_runs() -> list[tuple[Path, dict]]:
    """Every archived chat run whose latency may be cited. Usually empty until O-12."""
    out = []
    if not RUNS.exists():
        return out
    for run_dir in sorted(RUNS.iterdir()):
        chat = run_dir / "chat.json"
        if not run_dir.is_dir() or not chat.exists() or is_stale(run_dir):
            continue
        try:
            record = json.loads(chat.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if latency_quotable(record):
            out.append((run_dir, record))
    return out


def audit_archive() -> dict:
    """Summarise what the archive may and may not be used for."""
    stale, shared, quotable, unmarked = [], [], [], []
    if RUNS.exists():
        for run_dir in sorted(RUNS.iterdir()):
            chat = run_dir / "chat.json"
            if not run_dir.is_dir() or not chat.exists():
                continue
            if is_stale(run_dir):
                stale.append(run_dir.name)
                continue
            try:
                record = json.loads(chat.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            meta = record.get("_meta") or {}
            if meta.get("latency_quotable") is True:
                quotable.append(run_dir.name)
            elif meta.get("host_class") == "shared":
                shared.append(run_dir.name)
            else:
                unmarked.append(run_dir.name)
    return {
        "quotable_latency": quotable,
        "shared_host_not_quotable": shared,
        "fidelity_stale": stale,
        "unmarked_treated_as_not_quotable": unmarked,
    }


if __name__ == "__main__":
    report = audit_archive()
    print(json.dumps(report, indent=2))
    if not report["quotable_latency"]:
        print("\nNo run in the archive may supply a latency figure.")
        print("Expected until the O-12 physical sitting (COMPETITION.md section 9g).")
