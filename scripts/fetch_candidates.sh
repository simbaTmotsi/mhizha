#!/usr/bin/env bash
# BUILD TIME ONLY. Downloads bake-off candidate GGUFs to models/bakeoff/.
#
# Nothing here runs at inference time, on a phone or in the judged sandbox. The ADTC
# submission fetches its single chosen model through download_model.sh instead.
#
# Idempotent: an existing file of the right size is left alone. Records sha256 for every
# candidate so a bake-off row can name the exact bytes it measured.

set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEST="$HERE/models/bakeoff"
MANIFEST="$HERE/competition/candidates.yaml"
HASHES="$HERE/competition/candidate_hashes.txt"

mkdir -p "$DEST"

only="${1:-all}"

# Parse the manifest with python rather than sed: the manifest is the source of truth
# and a shell-parsed copy of it would drift.
mapfile -t ROWS < <(python3 - "$MANIFEST" "$only" <<'PY'
import sys, yaml
manifest = yaml.safe_load(open(sys.argv[1]))
only = sys.argv[2]
rows = list(manifest.get("candidates") or [])
smoke = manifest.get("smoke")
if smoke:
    rows.append(smoke)
for c in rows:
    if only not in ("all", c["id"]):
        continue
    print(f"{c['id']}\t{c['repo']}\t{c['file']}")
PY
)

if [[ ${#ROWS[@]} -eq 0 ]]; then
  echo "no candidate matched '$only'" >&2
  exit 1
fi

echo "fetching ${#ROWS[@]} candidate(s) into $DEST"

for row in "${ROWS[@]}"; do
  IFS=$'\t' read -r id repo file <<< "$row"
  out="$DEST/$id.gguf"
  url="https://huggingface.co/$repo/resolve/main/$file"

  if [[ -f "$out" ]]; then
    echo "  [skip] $id already present ($(du -h "$out" | cut -f1))"
    continue
  fi

  echo "  [get ] $id  <- $repo/$file"
  if ! curl -L --fail --progress-bar -o "$out.partial" "$url"; then
    echo "  [FAIL] $id could not be downloaded from $url" >&2
    rm -f "$out.partial"
    continue
  fi
  mv "$out.partial" "$out"
  echo "  [ok  ] $id  $(du -h "$out" | cut -f1)"
done

echo
echo "recording sha256 (this takes a moment over several GB)…"
: > "$HASHES"
{
  echo "# sha256 of every downloaded bake-off candidate."
  echo "# Regenerate with scripts/fetch_candidates.sh. Referenced by docs/BAKEOFF.md."
  echo "# recorded: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
} >> "$HASHES"
for f in "$DEST"/*.gguf; do
  [[ -f "$f" ]] || continue
  printf '%s  %s  %s bytes\n' \
    "$(sha256sum "$f" | cut -d' ' -f1)" \
    "$(basename "$f")" \
    "$(stat -c%s "$f")" >> "$HASHES"
done

echo "wrote $HASHES"
cat "$HASHES"
