#!/usr/bin/env bash
# ADTC 2026 submission model download.
#
# Required by the official template. Runs BEFORE the profiler starts; once profiling
# begins no outbound request is permitted, and none is made.
#
# Rules honoured (template README):
#   - idempotent: an existing final model is left alone
#   - no credentials: a public Hugging Face URL
#   - output path matches `_runtime.model_path` in metadata.json exactly
#
# BAKE AT DOWNLOAD, RATHER THAN RE-HOSTING
# ----------------------------------------
# This script fetches the STOCK UPSTREAM GGUF and applies our chat-template changes
# locally, here, before profiling starts. We host nothing.
#
# Why that is worth the extra step:
#   - the bytes we download are upstream's, and their hash is verifiable against the
#     original public repo
#   - no derivative work is redistributed, so no re-hosting obligations attach. For
#     Llama-family models that matters concretely: the Llama 3.2 Community License
#     requires a derivative model's NAME to begin with "Llama", plus a "Built with Llama"
#     notice and a bundled Agreement copy
#   - one less piece of infrastructure to keep alive between now and judging
#
# bake_template.py is PYTHON STANDARD LIBRARY ONLY, by design. No pip, no `gguf` package,
# no numpy. The evaluator's environment is not ours to install into, and a bake step that
# needed `pip install` would be a submission that fails on someone else's machine.
#
# If the bake fails for any reason, the script FAILS LOUDLY rather than silently shipping
# an unbaked model: the two behave differently enough (see COMPETITION.md section 9b) that
# quietly falling back would make the submission unreproducible.

set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODEL_DIR="$HERE/model"

# Upstream stock weights, PINNED TO A REVISION.
#
# `main` is a moving target: a repacker can push new weights under the same filename at
# any time, and the profiler's audit run downloads fresh. Pinning the commit plus
# verifying sha256 means the bytes the judges profile are exactly the bytes we measured,
# or the script stops. An unnoticed upstream change would silently invalidate every
# number in REPORT.md.
STOCK_REV="f6d5376be1edb4d416d56da11e5397a961aca8ae"
STOCK_URL="https://huggingface.co/unsloth/Qwen3.5-2B-GGUF/resolve/${STOCK_REV}/Qwen3.5-2B-Q4_K_M.gguf"
STOCK_SHA256="aaf42c8b7c3cab2bf3d69c355048d4a0ee9973d48f16c731c0520ee914699223"
STOCK_BYTES="1280835840"
STOCK_FILE="$MODEL_DIR/.stock-Qwen3.5-2B-Q4_K_M.gguf"

# Final artifact, and the exact path metadata.json declares in _runtime.model_path.
MODEL_FILE="$MODEL_DIR/mhizha-Qwen3.5-2B-Q4_K_M.gguf"

mkdir -p "$MODEL_DIR"

if [[ -f "$MODEL_FILE" ]]; then
  echo "model already present at $MODEL_FILE - skipping"
  exit 0
fi

if [[ ! -f "$STOCK_FILE" ]]; then
  echo "downloading stock weights: $STOCK_URL"
  if command -v curl > /dev/null 2>&1; then
    curl -L --fail --progress-bar -o "$STOCK_FILE.partial" "$STOCK_URL"
  elif command -v wget > /dev/null 2>&1; then
    wget --show-progress -O "$STOCK_FILE.partial" "$STOCK_URL"
  else
    echo "error: neither curl nor wget found" >&2
    exit 1
  fi
  mv "$STOCK_FILE.partial" "$STOCK_FILE"
else
  echo "stock weights already present at $STOCK_FILE"
fi

# ---- verify the downloaded bytes BEFORE baking -----------------------------------
# Baking a file we have not verified would propagate a bad download into the artifact the
# judges run, and the bake's own tensor-hash guard only proves the bake was faithful to
# whatever it was given.
actual_bytes="$(wc -c < "$STOCK_FILE" | tr -d ' ')"
if [[ "$actual_bytes" != "$STOCK_BYTES" ]]; then
  echo "error: size mismatch for $STOCK_FILE" >&2
  echo "  expected $STOCK_BYTES bytes, got $actual_bytes" >&2
  echo "  Upstream may have republished under the pinned path, or the download truncated." >&2
  rm -f "$STOCK_FILE"
  exit 1
fi

sha_tool=""
for candidate in sha256sum shasum; do
  if command -v "$candidate" > /dev/null 2>&1; then
    sha_tool="$candidate"
    break
  fi
done

if [[ -n "$sha_tool" ]]; then
  if [[ "$sha_tool" == "shasum" ]]; then
    actual_sha="$(shasum -a 256 "$STOCK_FILE" | awk '{print $1}')"
  else
    actual_sha="$(sha256sum "$STOCK_FILE" | awk '{print $1}')"
  fi
  if [[ "$actual_sha" != "$STOCK_SHA256" ]]; then
    echo "error: sha256 mismatch for $STOCK_FILE" >&2
    echo "  expected $STOCK_SHA256" >&2
    echo "  actual   $actual_sha" >&2
    echo "  These are NOT the weights this submission was measured against. Stopping." >&2
    rm -f "$STOCK_FILE"
    exit 1
  fi
  echo "verified: sha256 matches the pinned revision"
else
  # Fall back to Python rather than skipping the check: an unverified download is the
  # one thing this section exists to prevent.
  if command -v python3 > /dev/null 2>&1; then
    python3 - "$STOCK_FILE" "$STOCK_SHA256" <<'PYEOF'
import hashlib, sys
path, expected = sys.argv[1], sys.argv[2]
h = hashlib.sha256()
with open(path, "rb") as fh:
    for chunk in iter(lambda: fh.read(8 << 20), b""):
        h.update(chunk)
actual = h.hexdigest()
if actual != expected:
    sys.stderr.write(
        "error: sha256 mismatch\n"
        "  expected %s\n  actual   %s\n"
        "  These are NOT the weights this submission was measured against.\n"
        % (expected, actual)
    )
    sys.exit(1)
print("verified: sha256 matches the pinned revision (python fallback)")
PYEOF
    if [[ $? -ne 0 ]]; then
      rm -f "$STOCK_FILE"
      exit 1
    fi
  else
    echo "error: no sha256 tool and no python3; cannot verify the download" >&2
    exit 1
  fi
fi

PY_BIN=""
for candidate in python3 python; do
  if command -v "$candidate" > /dev/null 2>&1; then
    PY_BIN="$candidate"
    break
  fi
done
if [[ -z "$PY_BIN" ]]; then
  echo "error: no python interpreter found; cannot apply the chat template" >&2
  exit 1
fi

echo "baking chat template with $PY_BIN (standard library only, no pip)"
"$PY_BIN" "$HERE/bake_template.py" --in "$STOCK_FILE" --out "$MODEL_FILE"

if [[ ! -s "$MODEL_FILE" ]]; then
  echo "error: bake produced no output at $MODEL_FILE" >&2
  exit 1
fi

# Drop the stock copy once the bake has succeeded. Keeping both doubles peak disk in the
# sandbox for no benefit: re-running this script short-circuits on MODEL_FILE existing.
rm -f "$STOCK_FILE"

echo "done: $MODEL_FILE"
