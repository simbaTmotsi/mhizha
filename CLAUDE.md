# Mhizha

Offline-first, on-device AI agronomy co-pilot for Zimbabwean smallholder farmers.
Formerly named Hurudza. ADTC 2026 entry, now in build stage.

Mhizha answers practical agronomy questions (crop selection, planting calendars, pest
and disease identification and management, soil and fertiliser, water and irrigation,
post-harvest handling) grounded in a curated, human-validated Zimbabwean agronomic
corpus. It runs entirely on a mid-range Android phone with no connectivity.

---

## Standing rules

These five rules override any default approach. If a rule conflicts with a convenient
library, framework, or pattern, the rule wins and the convenience is dropped.

### 1. Fully offline at inference

No network calls at runtime. Not for models, not for embeddings, not for telemetry, not
for analytics, not for crash reporting, not for a "quick fallback to the cloud when the
local model is unsure". Anything that needs the internet (model download, corpus source
fetching, index build) happens at build time on a developer machine, never on the
farmer's device.

Enforcement: runtime modules under `src/mhizha/{rag,llm,app,i18n}/` must not import
`requests`, `httpx`, `urllib`, `socket`, or any SDK that opens a connection. Build-time
modules under `src/mhizha/corpus/` may, and must say so in their module docstring.
`tests/test_offline.py` asserts this by static import scan and must stay green.

### 2. On-device, inside a hard memory budget

Target device is defined in `config.yaml` under `device`. The primary profile is a
**4 GB RAM Android phone**, which in practice gives an app roughly 1.2 to 1.8 GB of
headroom before the low-memory killer intervenes. Every runtime component has to fit
together inside that: quantized LLM weights, embedding model, vector index, KV cache,
and the app itself.

No component may assume a GPU, a server, a background daemon, or more than one file on
disk when one file will do. Model choice is never hardcoded. `src/mhizha/llm/registry.py`
reads the device profile from config and resolves a candidate model against the budget.
Adding a model means adding an entry with its measured on-disk and resident size, not
editing an `if` statement.

### 3. Grounded, cited, and willing to abstain

Every answer is grounded in retrieved corpus passages. The generator never answers from
parametric knowledge.

- If retrieval confidence is below the abstention threshold in config, Mhizha abstains or
  asks one clarifying question. It does not guess.
- Every answer surfaces what it was based on: source title, publisher, and refresh date
  of each passage used.
- Mhizha never fabricates agronomic facts. It is most conservative about agrochemical
  names, active ingredients, dosages, mixing rates, pre-harvest intervals, and re-entry
  periods. A dosage that is not verbatim in a retrieved, validated passage is not
  emitted, ever, in any phrasing, including "typically" or "around".
- Answers that touch chemical application carry the safety notice from the active locale
  and a referral to a local AGRITEX extension officer.

Enforcement: `src/mhizha/app/safety.py` is the single choke point. It runs after
generation and before display. Every rule in it has a test in `tests/test_safety.py`.

### 4. The corpus is authoritative and human-validated

We build the ingestion, schema, and pipeline. We do not author agronomic content.

- Where content is missing, scaffold the structure and register the gap in
  `data/SOURCES.md`. Never write a plausible-sounding fact to fill a hole.
- Everything currently in `data/corpus/` is **placeholder**, machine-detectable by the
  `placeholder: true` front-matter flag, and is excluded from any answer served in a
  non-development profile.
- Every chunk carries `validated: false` until a named human reviewer signs it off in the
  review ledger (`data/review_ledger.jsonl`). `retrieval.validated_only` in config
  controls whether unvalidated chunks may be served.
- `source` and `refresh_date` are first-class required fields on every chunk. They are
  what make an answer defensible to a farmer and to an extension officer. A chunk without
  them fails ingestion.

### 5. Local languages are a design seam, not a later feature

English, Shona (`sn`), and Ndebele (`nd`). No user-facing string is hardcoded in code.
All copy lives in `src/mhizha/i18n/locales/<lang>.yaml` and is fetched through
`src/mhizha/i18n`. Translations that do not exist yet are marked `TODO_TRANSLATE` and
fall back to English at runtime with the fallback recorded, never silently.

Retrieval must tolerate a query in one language against a corpus in another. The
embedder choice in config carries a `multilingual` flag, and the cross-language path is
documented in `docs/model-shortlist.md`.

---

## Architecture

```
farmer question
      |
      v
[i18n] detect/normalize language ---------------+
      |                                         |
      v                                         |
[rag.embedder] local quantized sentence embedder|
      |                                         |
      v                                         |
[rag.store] sqlite-vec single-file index        |
      |  (numpy brute-force fallback)           |
      v                                         |
[rag.retrieve] top-k + confidence score         |
      |                                         |
      +--> confidence < threshold --> abstain / clarify
      |                                         |
      v                                         |
[llm.prompts] grounded prompt, passages only    |
      |                                         |
      v                                         |
[llm.base] pluggable backend                    |
      |  stub (dev) | llama.cpp (dev harness)   |
      |  MediaPipe / MLC-LLM (Android)          |
      v                                         |
[app.safety] grounding + agrochemical guard     |
      |                                         |
      v                                         |
answer + sources + confidence <-----------------+
```

**Generation.** A quantized small language model in GGUF. The dev harness runs it through
`llama-cpp-python`. The Android app targets an on-device runtime (MediaPipe LLM Inference
or MLC-LLM). Backends sit behind `src/mhizha/llm/base.py::LLMBackend` so swapping runtime
never touches app logic. The default backend in a fresh checkout is the deterministic
extractive `stub`, so the pipeline runs end to end with no model download.

**Retrieval.** `sqlite-vec` is the on-device target: the whole index is one `.db` file we
can ship in the APK assets or pull from the device filesystem. Where the extension cannot
be loaded, `src/mhizha/rag/store.py` falls back to a numpy brute-force scan over vectors
stored as BLOBs in that same sqlite file. Same file, same schema, same interface.

**Embedding.** A small local sentence embedder, int8-quantized for device. Candidates and
their sizes live in `docs/model-shortlist.md`. No cloud embeddings, at build time or at
runtime.

**Corpus pipeline.** `ingest -> clean -> chunk (+metadata) -> embed -> index`. Metadata
schema is in `src/mhizha/corpus/schema.py` and is the contract every stage honours.

---

## Directory layout

```
CLAUDE.md               this file
README.md               setup, offline notes, Android deployment path
Makefile                ingest / index / ask / eval / test entry points
config.yaml             device profile, model choice, thresholds, locales
requirements.txt        build-time deps (dev machine only)

.claude/agents/         subagent definitions (one role each)
.claude/skills/         reusable skills, one SKILL.md per directory

src/mhizha/
  config.py             typed config loader, single source of truth
  cli.py                typer CLI: ingest, index, ask, eval, doctor
  corpus/               BUILD TIME ONLY. network allowed here.
    schema.py           Document / Chunk dataclasses, required fields
    ingest.py           adapters: markdown, txt, pdf, docx
    clean.py            normalisation, dehyphenation, boilerplate strip
    chunk.py            metadata-preserving chunker
    review.py           human validation ledger
  rag/                  RUNTIME. no network.
    embedder.py         local embedding model wrapper
    store.py            sqlite-vec store + numpy fallback
    index.py            index build (build time), index open (runtime)
    retrieve.py         top-k retrieval + confidence scoring
  llm/                  RUNTIME. no network.
    base.py             LLMBackend protocol
    stub.py             deterministic extractive backend (default)
    llamacpp.py         llama-cpp-python backend (dev harness)
    prompts.py          grounded prompt templates, per locale
    registry.py         model shortlist + RAM budget resolver
  app/                  RUNTIME. no network.
    answer.py           orchestration: retrieve, ground, generate, cite
    safety.py           abstention, grounding check, agrochemical guard
  i18n/                 locale loading and fallback
    locales/{en,sn,nd}.yaml

data/
  raw/                  drop source PDFs and DOCX here (gitignored)
  corpus/               ingestible documents. currently PLACEHOLDER only.
  index/                built artefacts (gitignored)
  SOURCES.md            gap register: what we still need, and from whom
  review_ledger.jsonl   human sign-off records

eval/                   abstention, red-team, and grounding eval sets
tests/                  pytest suite
docs/                   model shortlist, Android packaging path
```

---

## Coding conventions

- Python 3.10+. Type hints on every public function. `from __future__ import annotations`.
- Standard library first. Every added dependency must justify itself against the on-device
  budget and be labelled build-time or runtime in `requirements.txt`.
- Dataclasses over dicts for anything that crosses a module boundary.
- No user-facing string literals in code. Use `i18n.t(key, lang)`.
- No magic numbers. Thresholds, k values, chunk sizes, and budgets live in `config.yaml`.
- Module docstrings state `RUNTIME (offline)` or `BUILD TIME` on the first line.
- Errors surface as typed exceptions from `src/mhizha/errors.py`, never bare strings.
- No em dashes in code comments, docs, or commit messages.
- Never commit model weights, `data/raw/`, or `data/index/`.

## Testing requirement

**Every retrieval rule and every safety rule has a test. This is not optional and a
change that adds a rule without a test is not done.**

- `tests/test_offline.py` proves no runtime module can reach the network.
- `tests/test_retrieval.py` covers top-k ordering, metadata preservation, filter
  correctness, and confidence scoring at the threshold boundaries.
- `tests/test_safety.py` covers abstention below threshold, refusal to emit an ungrounded
  dosage, the agrochemical guard, and the citation requirement.
- `tests/test_corpus.py` covers schema enforcement: a chunk without `source` or
  `refresh_date` must fail ingestion.
- `eval/` holds the agronomy eval sets. `make eval` reports grounding rate, abstention
  precision and recall, and red-team pass rate. A red-team regression blocks a release.

Run `make test` before considering any task complete.

---

## Working agreements for agents

- Do not invent agronomic content. If you need a fact that is not in the corpus, add a
  gap entry to `data/SOURCES.md` and stop.
- Do not add a runtime network call. If you think you need one, you have misread rule 1.
- Do not hardcode a model name outside `config.yaml` and `llm/registry.py`.
- Model size figures in docs are approximate until measured on target hardware. Mark
  unmeasured figures `(approx, unverified)` rather than presenting them as fact.
- Prefer small, dependency-light, single-file-on-device choices over anything that
  assumes a server.
