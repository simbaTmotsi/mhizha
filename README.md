# Mhizha

An offline-first, on-device AI agronomy co-pilot for Zimbabwean smallholder farmers.
Formerly Hurudza. ADTC 2026 entry, in build stage.

Mhizha answers practical agronomy questions grounded in a curated, human-validated
Zimbabwean agronomic corpus, entirely on a mid-range Android phone with no connectivity.
When it does not have a validated source, it says so rather than guessing.

> **The corpus is empty of real content today.** Everything in `data/corpus/` is a
> structural placeholder that states no dates, rates, thresholds, or product names, and
> is flagged `placeholder: true`. The pipeline is real; the agronomy is not sourced yet.
> See [`data/SOURCES.md`](data/SOURCES.md) for the gap register.

## Quick start

```bash
make setup                                          # build time, needs network
make build                                          # ingest + chunk + index
make ask Q="when should I plant maize in Mashonaland"   # add L=sn for Shona
make test
make doctor                                         # device budget and health
make eval                                           # grounding, abstention, red-team
```

`make ask` runs fully offline. So does everything after `make setup`.

## What you get

```
Answer:     extracted from retrieved passages, every claim cited [P1]
Sources:    title, publisher, refresh date, and flags per passage
Confidence: a band (high / medium / low) with the score and its components
Notices:    placeholder warning, agrochemical safety notice where relevant
```

Below the abstention threshold the model is not called at all. Mhizha says what it does
not know, asks the one clarifying question that would unblock it, and refers the farmer to
their local AGRITEX extension officer.

## The five standing rules

These are in [`CLAUDE.md`](CLAUDE.md) in full and they override any convenient default.

1. **Fully offline at inference.** No network calls at runtime, for anything, ever.
   Model downloads and corpus builds happen at build time on a developer machine.
2. **On-device, inside a hard budget.** A 4 GB Android phone, roughly 1.4 GB of app
   headroom, shared between the model, the embedder, the index, and the KV cache.
3. **Grounded, cited, willing to abstain.** Every answer comes from retrieved passages.
   Low confidence means abstain, not guess. No dosage is ever emitted unless it appears
   verbatim in a validated passage.
4. **The corpus is authoritative and human-validated.** We build the pipeline. We do not
   author agronomic content. Gaps get registered, not filled with plausible text.
5. **Local languages are a design seam.** English, Shona, Ndebele. No hardcoded strings,
   and untranslated keys fall back to English visibly, never silently.

## How it works

```
question
  -> detect region and language
  -> embed locally (all-MiniLM-L6-v2, 384d)
  -> retrieve top-k from one sqlite file (sqlite-vec, numpy fallback)
  -> score confidence (top-1, margin, cross-document agreement)
  -> below threshold? abstain or clarify. The model is never called.
  -> R5 gate: question asks for a dose with no validated figure? refuse now.
  -> compose a grounded prompt, passages only, each with an id
  -> generate locally (stub by default, llama.cpp or MediaPipe/MLC on device)
  -> safety pass: citations, fabricated ids, agrochemical guard, injection
  -> answer + sources + confidence band
```

Read the code in this order: [`app/answer.py`](src/mhizha/app/answer.py) top to bottom,
then [`app/safety.py`](src/mhizha/app/safety.py), then
[`rag/retrieve.py`](src/mhizha/rag/retrieve.py).

## Setup detail

```bash
python3 -m pip install -r requirements.txt

# Embedder weights, build time only, stored locally and never fetched at runtime.
python3 -c "
from sentence_transformers import SentenceTransformer
SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2').save('models/embedder/all-MiniLM-L6-v2')
"
```

Without the weights, `embedder.allow_hash_fallback` gives you a deterministic hash
embedder so the pipeline still runs end to end. It proves the plumbing; it does not
produce useful retrieval, and `config.py` forbids it in the production profile.

### Running a real model

The default generation backend is `stub`: deterministic, extractive, no download. It only
emits sentences already present in the retrieved passages, which makes it a useful floor.
Anything a real model does worse than the stub is a regression.

```bash
pip install llama-cpp-python
make models                                # candidates with sizes and fit verdict
# download a GGUF that fits into models/llm/<model-id>.gguf
# then set llm.backend: llamacpp in config.yaml
make ask Q="..."
make eval --backend llamacpp               # safety properties against a real generator
```

## Adding real corpus content

```bash
cp your-document.pdf data/raw/
cat > data/raw/your-document.pdf.meta.yaml <<'YAML'
source: "Maize Production Guide 2025"
publisher: "AGRITEX"
refresh_date: "2025-09-01"     # required, ISO, never guessed
lang: en
crop: maize
region: mashonaland-central
season: summer
topic: planting-calendar
YAML

make ingest        # PDF, DOCX, markdown, and txt adapters
make chunk
python -m mhizha review status
python -m mhizha review sign <chunk_id> --reviewer "Name of a real person"
make index
```

Ingestion **fails** without `source`, `publisher`, `refresh_date`, and `lang`. That is
deliberate: a chunk we cannot attribute is a chunk we cannot defend to a farmer or an
extension officer, and an undated planting calendar is a liability. Re-ingesting a changed
source invalidates prior human sign-off, because a review of old text says nothing about
new text.

## Offline and on-device notes

**Offline.** `tests/test_offline.py` statically scans every runtime module and fails if
one imports `requests`, `httpx`, `urllib`, `socket`, or any similar library. It is a
static scan rather than a runtime check because a runtime check only catches calls on
paths the tests happen to exercise. Build-time code lives under `src/mhizha/corpus/` and
declares itself in its docstring.

On Android the enforcement is stronger still: the app requests **no network permission**,
so a network call fails at the syscall no matter what any library attempts. See
[`docs/android-packaging.md`](docs/android-packaging.md).

**On-device.** The index is one sqlite file, shippable in APK assets and openable
read-only with no server and no background service. `sqlite-vec` is the preferred
backend; where the extension will not load, the same file is read by a numpy brute-force
scan, and both return identical rankings. Run `make doctor` for the memory accounting
against the active device profile. See [`docs/model-shortlist.md`](docs/model-shortlist.md).

## Testing

```bash
make test        # 174 tests
make eval        # grounding, abstention, red-team, reported per category
```

Every retrieval rule and every safety rule has a test. That is a requirement, not a
convention: a change that adds a rule without a test is not done.

`make eval` reports per category and never blends into one number, because a single score
hides exactly the failure that matters. A red-team critical failure blocks release with no
deferral path. Cases marked `requires_generator` are skipped **loudly** against the stub
backend, because the stub cannot judge that an on-topic passage fails to answer a
question, and reporting those as failures would measure the harness rather than the
system.

## Known limitations

Honest ones, all tracked in [`data/SOURCES.md`](data/SOURCES.md):

- **No real agronomic content.** Gaps G-01 through G-07.
- **`retrieval.abstain_below` is an uncalibrated default** (G-14). Measured on the
  placeholder corpus, answerable and unanswerable questions overlap in similarity: an
  answerable case scores 0.463 while an out-of-corpus crop scores 0.487. No threshold
  separates them, so calibrating now would be fitting noise.
- **The embedder is English-only** (G-12). A Shona or Ndebele query cannot match an
  English passage. `make doctor` warns about this every run.
- **Shona and Ndebele are entirely untranslated** (G-10). Every locale value is
  `TODO_TRANSLATE` and falls back to English with the fallback recorded. Safety copy is
  flagged priority and must not be machine translated.
- **Region mapping is province-level only** (G-13). A farmer naming their district gets no
  region filter. That fails safe, but it does not protect them from the region near-miss.
- **All model sizes are estimates** (G-09). Nothing has been measured on a real handset,
  and the 4 GB profile has under 100 MB of headroom.

## Repo layout

```
CLAUDE.md              standing rules, architecture, conventions
config.yaml            every threshold, budget, and model choice
.claude/agents/        corpus-curator, rag-engineer, model-integrator,
                       app-engineer, agronomy-evaluator
.claude/skills/        ingest-corpus, chunk-and-embed, build-index, retrieval-qa,
                       on-device-inference, eval-agronomy, localize
src/mhizha/corpus/     BUILD TIME: ingest, clean, chunk, review ledger
src/mhizha/rag/        RUNTIME: embedder, store, index, retrieve
src/mhizha/llm/        RUNTIME: backends, prompts, registry
src/mhizha/app/        RUNTIME: answer orchestration, safety choke point
src/mhizha/i18n/       locales and recorded fallback
data/SOURCES.md        the gap register
eval/                  grounding, abstention, red-team sets
docs/                  model shortlist, Android packaging
```
