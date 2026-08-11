#!/usr/bin/env bash
# BUILD TIME. Diff upstream HEAD of both official repos against our pinned vendored commits.
#
# Run around 22 Aug 2026, before submitting.
#
# This is not routine hygiene. A change to the profiler Dockerfile's SIMD flags would
# INVERT the model choice: if the audit image gains AVX2, throughput stops being a
# near-write-off, larger candidates become viable, and the ranking in docs/BAKEOFF.md no
# longer holds. The runner-up fallback in config.yaml exists for exactly this.
#
# Scoring constants in the profiler README matter just as much: TPS_REFERENCE and
# RAM_LIMIT_GB are hardcoded in scripts/adtc_profile.py and asserted by
# tests/test_competition.py, which will fail loudly if they drift.

set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

# Pinned commits, recorded in COMPETITION.md section 1.
declare -A PINNED=(
  [adtc-2026-submission-template]="63ddc5422404f8ee112fc74d28e29764acd40a50"
  [adtc-profiler]="7adbe08f157e9b96a670426339aca2a519706bdc"
)

# Files where a change forces action rather than just a note.
CRITICAL_REGEX='Dockerfile|README\.md|schema/.*\.json|accuracy\.py|throughput\.py|memory\.py|thermal\.py|comparator\.py|cli\.py'

changed_any=0

for repo in "${!PINNED[@]}"; do
  pin="${PINNED[$repo]}"
  url="https://github.com/Africa-Deep-Tech-Foundation/$repo.git"
  echo "=============================================================="
  echo "$repo"
  echo "  pinned: $pin"

  head_sha="$(git ls-remote "$url" HEAD 2>/dev/null | awk '{print $1}')"
  if [[ -z "$head_sha" ]]; then
    echo "  [ERROR] could not reach $url. Check connectivity and re-run." >&2
    changed_any=1
    continue
  fi
  echo "  HEAD:   $head_sha"

  if [[ "$head_sha" == "$pin" ]]; then
    echo "  [ok] unchanged since we pinned it."
    continue
  fi

  changed_any=1
  echo "  [CHANGED] upstream has moved."

  if ! git clone --quiet "$url" "$WORK/$repo" 2>/dev/null; then
    echo "  [ERROR] clone failed; diff unavailable." >&2
    continue
  fi

  echo "  --- commits since our pin ---"
  git -C "$WORK/$repo" log --oneline "$pin..HEAD" 2>/dev/null | sed 's/^/    /' \
    || echo "    (pinned commit not an ancestor: history was rewritten or force-pushed)"

  echo "  --- files changed ---"
  files="$(git -C "$WORK/$repo" diff --name-only "$pin..HEAD" 2>/dev/null)"
  echo "$files" | sed 's/^/    /'

  critical="$(echo "$files" | grep -E "$CRITICAL_REGEX" || true)"
  if [[ -n "$critical" ]]; then
    echo
    echo "  *** CRITICAL FILES CHANGED ***"
    echo "$critical" | sed 's/^/    !! /'
    echo
    echo "  Required before submitting:"
    echo "    1. Read the diff. Pay particular attention to GGML_* flags in the"
    echo "       Dockerfile and to TPS_REFERENCE / RAM_LIMIT_GB in the README."
    echo "    2. make profile-image        # rebuild against the new definition"
    echo "    3. make test                 # scoring constants are asserted"
    echo "    4. make profile CANDIDATE=<winner> and CANDIDATE=<runner-up>"
    echo "    5. Update docs/BAKEOFF.md, REPORT.md, and COMPETITION.md section 1."
    echo
    echo "  If SIMD flags changed, the model choice may invert. Re-rank before shipping."
  fi

  # Surface the SIMD flags explicitly, changed or not: this is the line that matters most.
  if [[ -f "$WORK/$repo/Dockerfile" ]]; then
    echo "  --- current upstream SIMD flags ---"
    grep -E "GGML_(NATIVE|AVX|AVX2|AVX512|FMA|F16C)" "$WORK/$repo/Dockerfile" \
      | sed 's/^/    /' || echo "    (none found)"
  fi
done

echo "=============================================================="
if [[ "$changed_any" -eq 0 ]]; then
  echo "Both repos match our pinned commits. Nothing to do."
else
  echo "Upstream moved, or a check failed. Act on the notes above before submitting."
fi
exit "$changed_any"
