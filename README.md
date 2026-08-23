# Mhizha

An offline-first, on-device AI agronomy co-pilot for Zimbabwean smallholder farmers.
Formerly Hurudza. **ADTC 2026 Laptop LLM track entry, domain `agriculture`.**

Mhizha answers practical agronomy questions grounded in a curated, human-validated
Zimbabwean agronomic corpus, entirely on a mid-range Android phone with no connectivity.
When it does not have a validated source, it says so rather than guessing.

**We submit Qwen3.5 2B in Q4_K_M, template-baked**, chosen by a candidate-blind read of the
transcripts. Two minutes on what it does and why:
[`docs/video/mhizha.mp4`](docs/video/mhizha.mp4).

![Mhizha refusing to give a spray rate](https://raw.githubusercontent.com/simbaTmotsi/mhizha/master/docs/gallery/03-refuses-a-dose.png)

*Asked how much cypermethrin to mix, it gives no number at all. A dose that is not written,
word for word, in a passage a human has signed off is never emitted — not as an estimate,
not as a typical figure, not when pressed. For this user the dangerous failure is not
unhelpfulness, it is confidence.*

> **The corpus is empty of real content today.** Everything in `data/corpus/` is a
> structural placeholder that states no dates, rates, thresholds, or product names, and
> is flagged `placeholder: true`. The pipeline is real; the agronomy is not sourced yet.
> See [`data/SOURCES.md`](data/SOURCES.md) for the gap register.

## Quick start

```bash
make setup                                          # deps + embedder weights. Needs network, once
make build                                          # ingest + chunk + index
make ask Q="when should I plant maize in Mashonaland"   # L=en|sn|nd. sn adds a notice, not Shona
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

![A cited answer with its sources table](https://raw.githubusercontent.com/simbaTmotsi/mhizha/master/docs/gallery/02-cited-answer.png)

*Every answer surfaces what it was based on: source, publisher, refresh date and a retrieval
score per passage. The placeholder banner is real and appears on every answer until the
corpus is validated.*

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
5. **Local languages are a design seam, and the seam is still empty.** English, Shona,
   Ndebele carried through the locale layer and the retrieval path, with no hardcoded
   strings and untranslated keys falling back to English visibly rather than silently.
   **Nothing is translated yet and the model cannot answer in Shona or Ndebele**; see the
   limitations below before repeating the language claim anywhere.

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

## Languages, stated exactly

**The codes, since they are used throughout and expanded nowhere else:**

| code | language | endonym |
|---|---|---|
| `en` | English | |
| `sn` | Shona | chiShona |
| `nd` | Northern Ndebele, the Zimbabwean one | isiNdebele |

These are ISO 639-1, which is what BCP-47 uses where a two-letter code exists, and what the
submission template asks for. South Ndebele, spoken in South Africa, is a different language
with a different code (`nr`) and is not in scope here.

`metadata.json` declares `language_scope: ["en", "sn", "nd"]`. That is **the system being
built, not a capability the submitted artefact has today**, and the difference is worth
being precise about because it is the easiest claim here to overread.

| | today |
|---|---|
| the locale layer | works. `--lang sn` is carried through retrieval and rendering, no string is hardcoded, and an untranslated key falls back to English *visibly* |
| the Shona and Ndebele copy | **does not exist. 23 of 23 strings are `TODO_TRANSLATE`, in both locales.** `make doctor` prints the count every run |
| cross-language retrieval | **does not work.** The embedder is English-only, so a Shona query cannot match an English passage and the system abstains |
| the shipped model | **cannot answer in Shona or Ndebele** |

What `--lang sn` does today is therefore worth stating exactly, because it is easy to read
as more than it is. Run the same question at `L=en` and `L=sn` and diff the output: they are
byte-identical English apart from **one added line**, `language fallback to English for 1
string(s): translation not available yet`. The flag selects a locale, the locale is empty,
and the system tells you so rather than pretending. That visible fallback is the standing
rule working; it is not Shona output.

The bottom row is measured, not assumed. The behavioural probe includes one Shona question,
*"Ndinodyara chibage rini?"* — "when do I plant maize?". The 2B we ship read the verb as a
personal name and answered in English: *"Hello Ndinodyara. To give you the best advice,
could you tell me where you are located in Zimbabwe…"*. The two candidates we did not ship
did worse: one looped for several hundred tokens, the other produced nonsense Shona.
Transcripts are in [`runs/20260820T105919Z_blind/`](runs/20260820T105919Z_blind/).

The shipped model at least failed into English while still asking the province question its
baked template instructs, which is the safety posture holding where comprehension did not.
That is damage control, not coverage.

**So: say "Shona and Ndebele are a seam in the architecture, carried through the locale
layer and the retrieval path". Do not say "it speaks Shona".** Closing the gap needs a
multilingual embedder ([`docs/model-shortlist.md`](docs/model-shortlist.md) has the swap and
its size cost), human translation of the safety copy, and a model that handles the
languages, in that order.

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
| [`docs/VIDEO.md`](docs/VIDEO.md) | the 2-minute video: script, how it was made, what in it is presentation rather than measurement |
| [`docs/DEVPOST.md`](docs/DEVPOST.md) | the Devpost writeup |
| [`docs/gallery/`](docs/gallery/) | submission images, generated by `scripts/gallery.py` from material in this repository |

Two conventions in that work are worth naming because they are enforced by the test suite
rather than remembered. **No numeric figure is typed into `REPORT.md` by hand**: it is
measured (emitted by `scripts/report_figures.py` from an archived run), retrieved (an
official constant with its source), or derived (with its formula). And **no run that feeds a
submitted number may pass a flag the official profiler does not pass**, with the allowed set
derived from the vendored profiler source rather than hand-listed. A third: **absence fails
closed.** A missing measurement comes back as `Absent`, which raises on any numeric use
including truthiness, so a `x or 0.0` cannot quietly resurrect a zero and turn an unmeasured
candidate into a ranked one. That bug happened here once, which is why the type exists.

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
- **And the model itself cannot answer in Shona or Ndebele.** This is the limitation that
  bites hardest, because the competition profiles a bare GGUF and none of the layer above
  runs while judges score. Asked the Shona probe *"Ndinodyara chibage rini?"* ("when do I
  plant maize?"), the shipped 2B read the verb as a personal name and replied in English:
  *"Hello Ndinodyara. To give you the best advice, could you tell me where you are located
  in Zimbabwe…"*. It at least fell back to English and still asked the province question
  the baked template instructs; the two candidates we did not ship did worse, one looping
  and one producing nonsense Shona. Transcripts: `runs/20260820T105919Z_blind/`.
  **`language_scope` in `metadata.json` describes the system we are building, not a
  capability the submitted artefact has today.**
- **Region mapping is province-level only** (G-13). A farmer naming their district gets no
  region filter. That fails safe, but it does not protect them from the region near-miss.
- **All model sizes are estimates** (G-09). Nothing has been measured on a real handset,
  and the 4 GB profile has under 100 MB of headroom.

And on the measurement side, where they matter more:

- **We never had audit-class hardware.** No machine near the Standard Laptop spec was
  available to us, so submitted telemetry fell back to screened medians on our own shared
  host under a rule we dated in advance, and is labelled `FALLBACK` everywhere it appears
  with its measured spread printed beside it.
- **The report carries no latency figure at all.** Latency does not fall back: there is no
  honest substitute for judge-experienced latency on the judges' core topology. We published
  the absence and the reason instead. `scripts/report_figures.py` refuses to hand it over.
- **Throughput was not reproducible on that host.** Six repetitions of one model, warm-up
  discarded, threads fixed, every one at 0.00% CPU steal, spanned 67.9% of their own median.
  So we never claimed a candidate ordering on throughput, because we did not have one.

## How the submission artefacts are made

Nothing in the submission is a screenshot taken once and captioned from memory. The CLI
captures, the video, the gallery images and the caption file are all **generated from
material in this repository**, so a stale asset is a rebuild away rather than a re-shoot
away, and an asset cannot outlive the behaviour it claims.

```bash
make captures                          # CLI captures, from the shipped entry point
python3 scripts/gallery.py             # submission images, 3:2
python3 scripts/video_narration.py     # narration, seeded and bit-reproducible
python3 scripts/video_captions.py      # WebVTT, cue windows measured from the audio
cd video && npm run build              # the submitted video
```

**The first three work straight after `make setup`.** Pillow and imageio-ffmpeg are in
`requirements.txt`, labelled build time, never shipped.

**The last two need tooling that is deliberately not there.** The narration needs Kokoro,
and its dependency chain **does not build on Python 3.13**, which is the interpreter
`python3 -m venv` gives on current macOS: a spaCy dependency of the phoneme stack fails to
cythonize. Adding it would break `make setup`, which is the first command in this project's
own preflight, so it gets its own 3.12 interpreter instead. The video needs Node and
Remotion, which are not Python at all. `requirements.txt` carries the exact commands,
`docs/VIDEO.md` has the whole path, and `CITATIONS.md` section 7 lists every component with
its licence, including three GPL build-time tools and one that is not open source at all.

**Both are one-off**: the narration and the video are committed, so this is how to rebuild
them, not something anyone has to run to use the project.

The terminal beats in the video are **real executions**: the commands run in a pseudo-terminal
and the pause before output is the pause the machine actually took. Both video renderers read
one captured session file, so they cannot disagree about what the machine did.
[`docs/VIDEO.md`](docs/VIDEO.md) states plainly which two things in it are presentation
rather than measurement.

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
docs/video/            the submitted video, its narration, and the measured cue timings
video/                 Remotion composition, the renderer that drew the submitted video
CITATIONS.md           attributions and licences
```
