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
make setup                                          # deps + embedder weights. Needs network, once
make build                                          # ingest + chunk + index
make ask Q="when should I plant maize in Mashonaland"   # add L=sn for Shona
make test
make doctor                                         # device budget and health
make eval                                           # grounding, abstention, red-team
```

**Run them in that order.** `make setup` fetches the sentence embedder as well as the
Python dependencies, and `make ask` refuses to run without it rather than falling back to
the deterministic hash embedder that the test suite uses. The fallback would answer, but
with different retrieval than every figure and capture in this repository, and nothing on
screen would tell you that. `make embedder` fetches the weights on their own.

`make ask` runs fully offline. So does everything after `make setup`.

## What you get

```
Answer:     extracted from retrieved passages, every claim cited [P1]
Sources:    title, publisher, refresh date, and flags per passage
Confidence: a band (high / medium / low) with the score and its components
Notices:    placeholder warning, agrochemical safety notice where relevant
```

[`docs/SCREENSHOTS.md`](docs/SCREENSHOTS.md) shows all four paths as real captures: a cited
answer, an abstention, the agrochemical refusal, and the device budget. They are generated
by `python3 scripts/capture_cli.py` against the corpus in this repository, so they can be
re-run and diffed rather than taken on trust.

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
make setup        # both steps below

make deps         # python3 -m pip install -r requirements.txt
make embedder     # embedder weights, build time only, never fetched at runtime
```

`make embedder` is idempotent and skips when the weights are already there.

**Without the weights, `make ask` refuses and tells you how to fix it.** It does not fall
back. There is a deterministic hash embedder in the codebase, the test suite opts into it
explicitly so the suite never needs a download, and `embedder.allow_hash_fallback` defaults
to **false** everywhere else.

That default changed on 22 Aug 2026, and the reason is worth stating. It used to default
on, so a fresh clone with no weights answered questions using hashed tokens: every retrieval
result differed from ours, and nothing on screen said so. Anyone reproducing
[`docs/SCREENSHOTS.md`](docs/SCREENSHOTS.md) would have got different passages, different
scores and a different answer, and the reasonable conclusion from the outside is that our
captures were invented. A silent fallback that changes results is indistinguishable from
fabrication at a distance, so it is now loud and off by default, and every capture states
which embedder produced it.

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
make test        # the full suite
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

## The ADTC 2026 submission

This repository is also our ADTC 2026 Laptop LLM track entry. The competition profiles a
**bare GGUF**: the official profiler loads the model file directly and never executes any
code of ours, and the accuracy score comes from judges chatting with the live model. So the
retrieval and safety work above is the submission's evidence rather than the thing measured,
and the only channel from it into a judge's session is the chat template we bake into the
GGUF at download time.

```bash
bash download_model.sh          # pinned upstream weights, verified, template baked locally
make profile-image              # build the official profiler image from vendor/
make profile CANDIDATE=<id>     # run it; output archived under runs/
python3 scripts/report_figures.py   # what may be quoted, and what is blocked, with reasons
```

`download_model.sh` re-hosts nothing: it fetches the stock upstream GGUF at a pinned
revision, checks size and sha256, and applies the template locally with a standard-library
script. The bytes profiled are upstream's.

| Document | What it is |
|---|---|
| [`REPORT.md`](REPORT.md) | the technical writeup, and the only place figures are quoted |
| [`COMPETITION.md`](COMPETITION.md) | source of truth: every decision, measurement, and open item |
| [`competition/superseded.yaml`](competition/superseded.yaml) | every conclusion this project reversed, with the evidence, enforced by tests |
| [`docs/BAKEOFF.md`](docs/BAKEOFF.md) | candidate state |
| [`SUBMISSION.md`](SUBMISSION.md) | the ordered packaging-day runbook |
| [`CITATIONS.md`](CITATIONS.md) | attributions and licences |
| [`docs/SCREENSHOTS.md`](docs/SCREENSHOTS.md) | generated CLI captures |
| [`docs/VIDEO.md`](docs/VIDEO.md) | the 2-minute video script |

Two conventions in that work are worth naming because they are enforced by the test suite
rather than remembered. **No numeric figure is typed into `REPORT.md` by hand**: it is
measured (emitted by `scripts/report_figures.py` from an archived run), retrieved (an
official constant with its source), or derived (with its formula). And **no run that feeds a
submitted number may pass a flag the official profiler does not pass**, with the allowed set
derived from the vendored profiler source rather than hand-listed.

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
competition/           ADTC candidate manifest, superseded rules, constants
scripts/               ADTC measurement harness: bench, lm-eval, composite, figures
runs/                  archived run records, one directory per measurement
CITATIONS.md           attributions and licences
```
