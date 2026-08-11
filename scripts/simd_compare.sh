#!/usr/bin/env bash
# BUILD TIME. O-06: quantify the SIMD penalty in the official profiler image.
#
# Runs the SAME llama-bench command on the SAME model in two images that differ only in
# their GGML vector-extension flags:
#
#   adtc-profiler:latest  official, -DGGML_AVX=OFF -DGGML_AVX2=OFF -DGGML_FMA=OFF -DGGML_F16C=OFF
#   adtc-native:latest    identical, same pinned llama.cpp ref, AVX/AVX2/FMA/F16C ON
#
# THE NATIVE NUMBER IS NEVER SUBMITTED. Throughput, RAM, and thermal figures in the report
# come from the official image only (COMPETITION.md section 11). This measures a build-flag
# effect as an engineering finding, and tells us how much of the audit's throughput ceiling
# is a portability decision rather than a hardware limit.

set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CANDIDATE="${1:-smollm2-135m-instruct-q4_k_m}"
MODEL="$HERE/models/bakeoff/$CANDIDATE.gguf"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
OUT="$HERE/runs/${STAMP}_simd_${CANDIDATE}"

if [[ ! -f "$MODEL" ]]; then
  echo "error: $MODEL not found. bash scripts/fetch_candidates.sh $CANDIDATE" >&2
  exit 2
fi
if ! docker image inspect adtc-native:latest > /dev/null 2>&1; then
  echo "error: adtc-native:latest not built. Run: make native-image" >&2
  exit 2
fi

mkdir -p "$OUT"
echo "candidate: $CANDIDATE"
echo "run dir:   $OUT"
echo

# Identical invocation to the profiler's own (throughput.py): -p 512 -n 128 -ngl 0.
bench() {
  local image="$1" label="$2"
  echo "--- $label ($image) ---"
  docker run --rm --memory=7.5g --memory-swap=7.5g --cpus=4 \
    -v "$HERE/models/bakeoff:/m:ro" \
    --entrypoint llama-bench "$image" \
    -m "/m/$CANDIDATE.gguf" -p 512 -n 128 -ngl 0 --output json \
    > "$OUT/$label.json" 2> "$OUT/$label.stderr"
  local rc=$?
  if [[ $rc -ne 0 ]]; then
    echo "  FAILED (exit $rc). stderr:"; tail -5 "$OUT/$label.stderr" | sed 's/^/    /'
    return 1
  fi
  python3 - "$OUT/$label.json" <<'PY'
import json, sys
rows = json.load(open(sys.argv[1]))
pp = next((r for r in rows if r.get("n_gen", 0) == 0 and r.get("n_prompt", 0) > 0), None)
tg = next((r for r in rows if r.get("n_gen", 0) > 0), None)
print(f"  prompt processing: {pp['avg_ts']:.2f} tok/s" if pp else "  prompt processing: n/a")
print(f"  generation:        {tg['avg_ts']:.2f} tok/s" if tg else "  generation: n/a")
PY
}

bench adtc-profiler:latest official
echo
bench adtc-native:latest native
echo

python3 - "$OUT" <<'PY'
import json, pathlib, sys
out = pathlib.Path(sys.argv[1])

def rates(name):
    path = out / f"{name}.json"
    if not path.exists():
        return None, None
    rows = json.load(open(path))
    pp = next((r for r in rows if r.get("n_gen", 0) == 0 and r.get("n_prompt", 0) > 0), None)
    tg = next((r for r in rows if r.get("n_gen", 0) > 0), None)
    return (pp or {}).get("avg_ts"), (tg or {}).get("avg_ts")

o_pp, o_tg = rates("official")
n_pp, n_tg = rates("native")

summary = {
    "official_image": {"prompt_tok_s": o_pp, "generation_tok_s": o_tg},
    "native_avx2_image": {"prompt_tok_s": n_pp, "generation_tok_s": n_tg},
    "speedup_generation": round(n_tg / o_tg, 2) if o_tg and n_tg else None,
    "speedup_prompt": round(n_pp / o_pp, 2) if o_pp and n_pp else None,
    "tps_reference": 15.0,
    "official_meets_reference": (o_tg or 0) >= 15.0,
    "native_meets_reference": (n_tg or 0) >= 15.0,
    "label": "native figure is an ENGINEERING FINDING ONLY, never submitted",
}
(out / "simd_summary.json").write_text(json.dumps(summary, indent=2) + "\n")

print("=" * 62)
print(f"  official (SIMD off)  generation {o_tg}  prompt {o_pp}")
print(f"  native   (AVX2 on)   generation {n_tg}  prompt {n_pp}")
if summary["speedup_generation"]:
    print(f"  SIMD penalty: native is {summary['speedup_generation']}x faster at generation")
    print(f"                          {summary['speedup_prompt']}x faster at prompt processing")
print(f"  reference 15.0 tok/s: official {'MEETS' if summary['official_meets_reference'] else 'MISSES'},"
      f" native {'MEETS' if summary['native_meets_reference'] else 'MISSES'}")
print("=" * 62)
print(f"wrote {out}/simd_summary.json")
PY
