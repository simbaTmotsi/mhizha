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

WHY ABSENCE IS A TYPE
---------------------
Every consumer reads archived measurements through this module, and a measurement that is
not there comes back as `Absent`, not as `None` and never as `0.0`. `Absent` raises on any
numeric use, including truthiness, so missing data stops the calculation at the point it
is used rather than flowing onward as a plausible value.

This is not a hypothetical. `perf_band` once scored an unmeasured candidate `0.00`, which
charged five candidates the full 30% throughput weight for never having been benchmarked
and produced a finalist set of one that was an artefact of what had been measured. The
shape of that bug survives any single fix, because it is spelled `x or 0.0`, `.get(k, 0)`
and `if not x:` in ordinary-looking code. A type that refuses to be a number is the only
version of the rule that cannot be forgotten.

`tests/test_competition.py::test_numeric_consumers_read_only_through_run_guards` holds the
line: a consumer that opens `runs/` or a `bench.json` for itself fails the build.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
RUNS = REPO / "runs"

STALE_MARKER = "FIDELITY_STALE.txt"


class UnquotableFigure(RuntimeError):
    """A figure was requested from a run that is not permitted to supply it."""


@dataclass(frozen=True)
class Measurement:
    """A number that carries where it came from.

    Deliberately not a float subclass: a consumer has to call `float()` on it, which is
    the moment provenance could be dropped, and that moment is easy to find in review.
    """

    value: float
    field: str
    run_id: str

    present = True

    def __float__(self) -> float:
        return float(self.value)

    def __str__(self) -> str:
        return f"{self.value} ({self.field} from {self.run_id})"


@dataclass(frozen=True)
class Absent:
    """A measurement that does not exist. Fails closed on every numeric use.

    Truthiness raises too, because `x or 0.0` and `if not x:` are exactly how a missing
    measurement turns into a confident zero.
    """

    field: str
    run_id: str
    reason: str

    present = False

    def _refuse(self, *_args, **_kwargs):
        raise UnquotableFigure(
            f"refusing to use an absent measurement as a number.\n"
            f"  field:  {self.field}\n"
            f"  run:    {self.run_id}\n"
            f"  reason: {self.reason}\n"
            f"  Absence is not zero. Either measure it, or exclude this candidate from "
            f"the calculation explicitly (COMPETITION.md section 9f)."
        )

    __float__ = _refuse
    __int__ = _refuse
    __bool__ = _refuse
    __add__ = __radd__ = _refuse
    __sub__ = __rsub__ = _refuse
    __mul__ = __rmul__ = _refuse
    __truediv__ = __rtruediv__ = _refuse
    __lt__ = __le__ = __gt__ = __ge__ = _refuse
    __round__ = _refuse

    def __str__(self) -> str:
        return f"ABSENT ({self.field}: {self.reason})"


Figure = Measurement | Absent


def figure(record: dict, *keys: str, run_id: str, why: str = "") -> Figure:
    """Pull one numeric field out of a record as a `Measurement`, or `Absent`.

    `keys` walks nested mappings, so a caller names the measurement rather than
    navigating the file: figure(bench, "summary", cand, "min", run_id=rid).
    """
    field = "/".join(keys)
    node: object = record
    for key in keys:
        if not isinstance(node, dict) or key not in node:
            return Absent(field, run_id, why or f"{key!r} is not in the record")
        node = node[key]
    if node is None:
        return Absent(field, run_id, why or "recorded as null")
    try:
        return Measurement(float(node), field, run_id)
    except (TypeError, ValueError):
        return Absent(field, run_id, why or f"not numeric: {node!r}")


def is_stale(run_dir: Path) -> bool:
    return (run_dir / STALE_MARKER).exists()


# ------------------------------------------------------------------ archive access
#
# The archive is reached only through these. A consumer that globs `runs/` for itself
# also re-implements the guards by accident, which is how a stale or shared-host record
# gets read by something that did not know to check.


def read(path: Path) -> dict:
    """A run record, or an empty one. Never raises: a missing file is missing data."""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def newest_record(pattern: str, filename: str) -> tuple[str, dict, Path] | None:
    """The most recent (run_id, record, path) matching `runs/<pattern>/<filename>`."""
    matches = sorted(RUNS.glob(f"{pattern}/{filename}"), key=lambda p: p.stat().st_mtime)
    if not matches:
        return None
    path = matches[-1]
    return path.parent.name, read(path), path


def all_records(pattern: str, filename: str) -> list[tuple[str, dict]]:
    """Every (run_id, record) matching, oldest first by run id."""
    return [(p.parent.name, read(p)) for p in sorted(RUNS.glob(f"{pattern}/{filename}"))]


def record_at(path: Path) -> tuple[str, dict]:
    """A record named by path, for the case where the caller was given one on argv."""
    return path.parent.name, read(path)


def record_in(run_id: str, filename: str) -> dict:
    """A named file from a named run."""
    return read(RUNS / run_id / filename)


def physical_runs() -> list[str]:
    """Run ids that positively declare a physical host.

    Ordering claims between candidates are gated on this being non-empty: throughput
    measured on a shared host cannot separate candidates closer together than its own
    spread, so "A is faster than B" has no source until one of these exists.
    """
    out = []
    for run_id, record in all_records("*", "run.json"):
        if record.get("host_class") == "physical":
            out.append(run_id)
    for run_id, record in all_records("*_bench*", "bench.json"):
        if record.get("host_class") == "physical":
            out.append(run_id)
    return sorted(set(out))


def list_run_files(run_dir: Path, pattern: str) -> list[Path]:
    """Files matching a pattern inside one named run directory, sorted.

    Not an archive search: the caller already knows which run it wants. It lives here so
    that no consumer needs a glob of its own, which is the shape the door rule is written
    against, and so a future change to how runs are laid out has one place to happen.
    """
    return sorted(run_dir.glob(pattern))


def new_run_dir(stamp: str, kind: str) -> Path:
    """Where a consumer's own output is archived. Created on call."""
    out = RUNS / f"{stamp}_{kind}"
    out.mkdir(parents=True, exist_ok=True)
    return out


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
