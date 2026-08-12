#!/usr/bin/env python3
"""BUILD TIME. Derive the audit-fidelity oracle from the vendored profiler source.

WHY DERIVED RATHER THAN LISTED
------------------------------
The first version of this check carried a hand-written list of banned flags (`-t`,
`--numa`, `--mlock`, ...). That covers the instances someone thought of, which is exactly
the wrong shape: the next fidelity violation will be a flag nobody listed.

So the allowed set is READ OUT OF the profiler's own invocation. Anything the profiler
does not pass is forbidden by construction, without anyone having to anticipate it.

The snapshot is written to competition/fidelity_oracle.json with a sha256 of each source
region it was derived from. `tests/test_competition.py` re-derives on every run and fails
if the snapshot and the source disagree, so a profiler upgrade that changes the invocation
surfaces as a failing premise test rather than as silently stale rules.

Usage:
    python3 scripts/derive_fidelity_oracle.py          # print
    python3 scripts/derive_fidelity_oracle.py --write  # update the snapshot
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PROFILER = REPO / "vendor" / "adtc-profiler" / "src" / "adtc_profiler"
THROUGHPUT = PROFILER / "throughput.py"
ACCURACY = PROFILER / "accuracy.py"
SNAPSHOT = REPO / "competition" / "fidelity_oracle.json"


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _string_constants(node: ast.AST) -> list[str]:
    return [n.value for n in ast.walk(node)
            if isinstance(n, ast.Constant) and isinstance(n.value, str)]


def derive() -> dict:
    """Read the profiler's llama-bench invocation out of its own AST."""
    tree = ast.parse(THROUGHPUT.read_text(encoding="utf-8"))

    run_fn = next((n for n in tree.body
                   if isinstance(n, ast.FunctionDef) and n.name == "run_llama_bench"), None)
    if run_fn is None:
        raise SystemExit("run_llama_bench not found in throughput.py; layout changed")

    # The unconditional command list.
    cmd_assign = next(
        (n for n in ast.walk(run_fn)
         if isinstance(n, ast.Assign)
         and any(isinstance(t, ast.Name) and t.id == "cmd" for t in n.targets)
         and isinstance(n.value, ast.List)),
        None,
    )
    if cmd_assign is None:
        raise SystemExit("cmd = [...] literal not found in run_llama_bench")
    always = [s for s in _string_constants(cmd_assign.value) if s.startswith("-")]

    # Flags added inside a conditional: passed only when the caller supplies a value.
    conditional: list[str] = []
    for node in ast.walk(run_fn):
        if not isinstance(node, ast.If):
            continue
        for sub in ast.walk(node):
            if (isinstance(sub, ast.Call) and isinstance(sub.func, ast.Attribute)
                    and sub.func.attr in ("extend", "append")):
                conditional += [s for s in _string_constants(sub) if s.startswith("-")]

    # Does the profiler's own entry point ever supply the conditional argument?
    measure_fn = next((n for n in tree.body
                       if isinstance(n, ast.FunctionDef) and n.name == "measure"), None)
    if measure_fn is None:
        raise SystemExit("measure() not found in throughput.py")
    measure_passes = set()
    for node in ast.walk(measure_fn):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) \
                and node.func.id == "run_llama_bench":
            measure_passes = {kw.arg for kw in node.keywords if kw.arg}

    # Conditional flags the entry point never triggers are, in practice, never passed.
    n_threads_supplied = "n_threads" in measure_passes
    effective = sorted(set(always) | (set(conditional) if n_threads_supplied else set()))

    # Context length the profiler uses for in-process evaluation. Our chat harness mirrors
    # it rather than inventing one.
    acc_tree = ast.parse(ACCURACY.read_text(encoding="utf-8"))
    n_ctx = next(
        (n.value.value for n in acc_tree.body
         if isinstance(n, ast.Assign)
         and any(isinstance(t, ast.Name) and t.id == "_N_CTX" for t in n.targets)
         and isinstance(n.value, ast.Constant)),
        None,
    )

    return {
        "derived_from": {
            "throughput.py": sha256_of(THROUGHPUT),
            "accuracy.py": sha256_of(ACCURACY),
        },
        "llama_bench": {
            "always_passed": sorted(set(always)),
            "conditionally_passed": sorted(set(conditional)),
            "entry_point_supplies_conditional": n_threads_supplied,
            "effective_allowed": effective,
        },
        "accuracy_n_ctx": n_ctx,
        "note": (
            "ALLOWED = effective_allowed. Anything else is a fidelity violation on any "
            "run feeding a submitted number. Derived from source, not hand-listed, so a "
            "flag nobody anticipated is still caught."
        ),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()

    oracle = derive()
    print(json.dumps(oracle, indent=2))

    if args.write:
        SNAPSHOT.write_text(json.dumps(oracle, indent=2) + "\n", encoding="utf-8")
        print(f"\nwrote {SNAPSHOT}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
