#!/usr/bin/env python3
"""Runs INSIDE the profiler container. Scores one GGUF across the task mix.

Reuses `adtc_profiler.accuracy._make_lm`, which is the exact llama-cpp-python adapter the
official audit uses, so our ranking is produced by the same scoring path rather than a
lookalike of it. The only difference is that the model is loaded ONCE and evaluated
against several tasks, instead of once per task: on a slow CPU build the load and the
per-task warm-up dominate, and paying them four times over six candidates would cost
hours for nothing.

Emits one JSON object on stdout. Everything else goes to stderr so the caller can parse
stdout blindly.
"""
from __future__ import annotations

import json
import sys
import time


def main() -> int:
    model_path, tasks_csv, limit, seed = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
    tasks = [t.strip() for t in tasks_csv.split(",") if t.strip()]

    from adtc_profiler import accuracy

    if not accuracy.is_available():
        print(json.dumps({"error": "accuracy stack unavailable in this image"}))
        return 1

    import lm_eval

    started = time.time()
    lm = accuracy._make_lm(model_path)   # the audit's own adapter
    loaded = time.time()

    results = lm_eval.simple_evaluate(
        model=lm,
        tasks=tasks,
        limit=limit,
        random_seed=seed,
        numpy_random_seed=seed,
        fewshot_random_seed=seed,
    )
    finished = time.time()

    out = {"tasks": {}, "load_seconds": round(loaded - started, 1),
           "eval_seconds": round(finished - loaded, 1)}
    table = (results or {}).get("results") or {}
    for task in tasks:
        row = table.get(task)
        if not row:
            out["tasks"][task] = {"error": "no result"}
            continue
        extracted = accuracy._extract_score(row)   # prefers acc_norm, then acc
        if extracted is None:
            out["tasks"][task] = {"error": "no numeric metric", "keys": sorted(row)}
            continue
        score, metric = extracted
        n = ((results.get("n-samples") or {}).get(task) or {}).get("effective")
        out["tasks"][task] = {
            "score": round(float(score), 4),
            "metric": metric,
            "samples": int(n) if isinstance(n, int) else limit,
        }

    scored = [v["score"] for v in out["tasks"].values() if "score" in v]
    out["mean_score"] = round(sum(scored) / len(scored), 4) if scored else None
    out["tasks_scored"] = len(scored)
    print(json.dumps(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
