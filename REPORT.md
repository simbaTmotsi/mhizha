# Mhizha: an offline agronomy assistant for Zimbabwean smallholder farmers

**ADTC 2026 Laptop LLM track. Domain: agriculture.**

> **STATUS: SKELETON.** Numbers marked `[PENDING …]` land as measurements complete.
> Every figure in the finished document carries a label:
> **measured** (with a run id under `runs/`), **retrieved** (with a source), or
> **estimate** (and flagged as such). Nothing ships without one.

---

## 1. Problem

Smallholder farmers in Zimbabwe make decisions with real consequences (what to plant, when
to plant it, whether the marks on a leaf mean an intervention is worth its cost) with
patchy access to extension advice and, in much of the country, patchy or no connectivity.
An assistant that needs a network is not available at the moment those decisions are made.

Mhizha is an offline agronomy co-pilot for that user: a mid-range Android phone, no
connectivity, in a field.

**Why this is a load-bearing cross-disciplinary pairing rather than a theme.** The
agronomy dictates the architecture at three points that a general-purpose assistant would
not have:

1. **A validated-source dosage gate.** An agrochemical rate that is not verbatim in a
   human-signed-off passage is never emitted, in any phrasing, including "typically" or
   "around". A wrong spray rate destroys a season or harms the person applying it.
2. **A named-region hard filter.** Zimbabwe's provinces differ enough in rainfall that one
   province's planting calendar is actively wrong advice in another. A question naming a
   province excludes other provinces' content outright rather than ranking it lower.
3. **A quantity-intent gate.** A question asking for a dose is refused *before* generation
   when no validated figure exists, rather than filtered afterwards.

**What we deliberately do not do:** we did not author agronomic content. The corpus
shipped in this repository is structural placeholder, machine-detectable by a
`placeholder: true` flag, and states no dates, rates, thresholds or product names. Gaps
are registered in `data/SOURCES.md` with the organisation that would hold each one.
Inventing plausible agronomy to make a demo look complete would produce exactly the
failure the whole system exists to prevent: a fluent, cited, wrong answer.

---

## 2. Design decisions

### 2.1 What the competition actually scores, and what follows from it

The first substantive finding of this project was that **the profiler never executes
participant code**. A submission is `metadata.json`, `download_model.sh` and one GGUF; the
harness runs `llama-bench` for throughput and lm-eval against the model directly
(`vendor/adtc-profiler/src/adtc_profiler/cli.py`). `S_acc` is then produced by judges
chatting with the live model.

That reshaped the plan rather than decorating it. Our retrieval pipeline, confidence
scoring and safety rules cannot move the measured numbers. They are the submission's
*evidence and story*, and the honest consequence is that **every accuracy figure we
produce is an internal proxy**, labelled as such throughout, never presented as a
prediction of what a judge will score.

`[PENDING: final model selection and the composite that produced it]`

### 2.2 The one channel from our work into the judge's session

Since no code of ours runs, the GGUF's embedded `tokenizer.chat_template` is the only
channel carrying any of our design into a judge's chat. We verified it works rather than
assuming: `llama-server`'s `/apply-template` shows a template's default system branch
injected verbatim when the caller sends no system message.

Two things are baked, and the second matters more than the first:

- **An agronomy posture and refusal stance.** Safety behaviour only. It contains no
  planting date, no dosage, no product name. A build test fails if a quantity or a month
  name appears in it, because a baked fact is an invented fact delivered with no source.
- **Reasoning forced off**, for models whose template branches on `enable_thinking`.

**The reasoning finding.** Stock Qwen3.5-0.8B through the judge path returned **empty
content on every turn**: it spent its whole token budget inside an unclosed `<think>`
block (`finish_reason: length`), with the text in a separate `reasoning_content` field. A
judge would wait minutes and see a blank box. The model's own template defaults thinking
*off*, but `llama-server` sets `enable_thinking` true, overriding it, and the client-side
fix is a flag only the caller can send. Baking `{%- set enable_thinking = false -%}`
restores visible output. lm-eval would never have revealed this, because loglikelihood
scoring never generates.

### 2.3 Packaging: bake at download, host nothing

`download_model.sh` fetches the **stock upstream GGUF at a pinned revision**, verifies
size and sha256, and applies the template locally with a **standard-library-only** script
before profiling starts. Nothing is re-hosted.

This was not the first plan. The alternative was to re-host a modified GGUF, which brings
derivative-redistribution obligations (the Llama 3.2 licence, for instance, requires a
derivative model's name to *begin with* "Llama", plus a "Built with Llama" notice and a
bundled agreement copy). Baking at download avoids all of it: the bytes the judges profile
are upstream's and hash-verifiable, the transformation is auditable in twenty lines of
readable Python, and there is no private repository to remember to make public.

The baker is stdlib-only because the `gguf` package is **absent** from the official
profiler image and the evaluator's environment is not ours to install into. It parses the
GGUF container by hand and runs two guards on every bake: a **no-op round-trip** (rewriting
with the unchanged template must reproduce the file byte for byte, catching a lossy
rewriter even when its output loads) and **sha256 equality on the tensor-info and data
regions**. Both fail loudly and delete the output. A corrupted tensor region would not
necessarily crash llama.cpp; it could produce a model that loads and generates subtly
wrong output, which is worse.

### 2.4 Model selection

`[PENDING: composite table from docs/BAKEOFF.md]`

Candidates, all Q4_K_M GGUF: Llama 3.2 1B, Qwen3.5 0.8B / 2B / 4B, Gemma 4 E2B,
Phi-4-mini. Selection weights mirror the leaderboard (0.5 accuracy proxy, 0.3 throughput,
0.2 efficiency), with **throughput differences smaller than measured host noise treated as
ties** rather than as ordering.

`[PENDING: winner, runner-up fallback, and the reasoning]`

### 2.5 Fine-tuning

Not undertaken for Gate 1. The trigger for reconsidering was defined in advance and
narrowly: stock candidates failing *basic agronomy chat*, not merely scoring lower than we
would like. `[PENDING: whether the qualitative pass triggered it]`

---

## 3. Constraints

| Constraint | Consequence |
|---|---|
| 8 GB RAM, 4 vCPU, CPU-only, no GPU | Every candidate is a small quantised GGUF; `-ngl 0` throughout |
| `RAM_LIMIT_GB = 7.0` in the scoring formula (**retrieved**) | Efficiency falls linearly with model size; a 2.6 GB model forfeits ~37 points of `S_eff` before generating a token |
| `TPS_REFERENCE = 15.0`, fixed (**retrieved**) | Throughput saturates, so speed beyond the reference earns nothing |
| Offline once profiling begins | No network in any runtime path |
| llama.cpp / GGUF only | Fixes the runtime; the Android product targets the same family |
| The product target is a **4 GB phone**, not this laptop | Laptop measurements do not resolve phone gaps, and are not reported as if they do |

### The constraint that is not in the formula

The judge who scores accuracy also **waits through generation**. At measured rates a
300-token answer takes roughly 1.2 minutes on the smallest candidate and an estimated 14
minutes on a 4B. A four-prompt session on a large model runs close to an hour. The risk is
not the ~0.7 points of `S_perf` at stake; it is a depressed accuracy score or a truncated
session, which is a 50%-weight consequence arriving through a term nothing measures.

---

## 4. Benchmarks and measurement

> This section is deliberately as much about **how** the numbers were obtained as what
> they are. Several of our early figures were wrong, and the corrections are more
> informative than the originals.

### 4.1 Headline

`[PENDING: final telemetry from the O-12 physical machine]`

| Metric | Value | Source |
|---|---|---|
| Tokens/sec (generation) | `[PENDING]` | official image, physical machine |
| First-token latency | `[PENDING]` | same run |
| Peak RSS | `[PENDING]` | same run |
| Core temperature | `[PENDING]` | same run |

### 4.2 Throughput is harder to measure than it looks

Two runs of the same model, same benchmark, same image disagreed by **2.5x** (1.82 vs
4.50 tok/s). Chasing that produced the most useful engineering result in this project.

**It was not a methodology difference.** The profiler and our harness issue a
byte-identical `llama-bench` command and read the same `avg_ts` field.

**It was not CPU steal.** Three back-to-back repetitions, every one at **0.00% steal**,
still spanned 3.42 to 4.48 tok/s: **27.8% of the median**. Steal accounting sees stolen
CPU *time*, not stolen memory bandwidth or last-level cache.

**The 1.82 was an outlier.** Pooling five official-image samples gives 3.42 to 4.91 around
a median of 4.29, with 1.82 below all of them.

Two candidate explanations remain and three points cannot separate them: the repetitions
rise *monotonically*, which favours warm-up (page cache, mmap faulting, frequency ramp),
while the original pair moved generation 2.47x against prompt processing 1.30x, which
favours bandwidth contention, since generation is bandwidth-bound and prompt processing is
compute-bound. `[PENDING: O-13 resolution]`

**What we changed as a result:** ranking throughput is measured with steal screening,
interleaved candidates, warm-up discard and medians-with-spread; and **throughput gaps
narrower than the measured noise are reported as ties, not as ordering**.

### 4.3 The reference harness disables SIMD, and what that costs

The official image compiles llama.cpp with every vector extension off
(`GGML_AVX/AVX2/FMA/F16C=OFF`) for portability across audit VMs. Rebuilding it identically
except for those flags, at the same pinned llama.cpp ref:

| Build | Median (tok/s) | Samples | Spread |
|---|---|---|---|
| Official (SIMD off) | 4.29 | 3.42, 3.80, 4.29, 4.48, 4.91 | 35% |
| Native (AVX2/FMA/F16C) | 5.59 | 4.53, 5.59, 6.01 | 26.5% |

**Ratio of medians 1.30x, with overlapping distributions** (native minimum 4.53 sits below
official maximum 4.91). An earlier single-run pair suggested 2.11x; that figure was wrong
and is retracted. On a host with 26 to 28% repeatability, a 1.3x effect is at the edge of
what can be resolved, and we say so rather than reporting a clean number.

### 4.3.1 Which code path runs on which build

The SIMD flags apply to the **binaries only**, and the reference image therefore contains
two differently-compiled copies of ggml. Every measured path maps to one of them:

| Code path | What it measures | Dockerfile stage | Vector extensions |
|---|---|---|---|
| `llama-bench` | **throughput, memory, thermals** (the submitted telemetry) | stage 1 | **OFF** (`GGML_AVX/AVX2/AVX512/FMA/F16C=OFF`) |
| `llama-server` | **judge chat**, and our qualitative pass | stage 1 | **OFF**, same binary build |
| `llama-cpp-python` | **accuracy** (lm-eval, in-process) | stage 2 | **ON** (only `GGML_NATIVE=OFF` is set, leaving the individual flags at their CMake defaults) |

Verified directly rather than inferred from the Dockerfile:
`llama_cpp.llama_print_system_info()` reports `AVX = 1 AVX2 = 1 F16C = 1 FMA = 1` in the
**stock** official image.

**A submission's throughput is measured on a SIMD-disabled binary, and its accuracy is
computed on a SIMD-enabled one.** The benchmarked speed is slower than the speed at which
the model is actually evaluated. The judge-facing chat path sits on the slower build, so
the latency a judge experiences matches the benchmarked figure rather than the accuracy
one, which is at least the conservative direction.

We report this as a finding, not a complaint. A harness that runs identically on any audit
VM is a defensible goal and quantifying its cost is more useful than assuming it. But if
uniform portability was the intent, stage 2 does not currently match stage 1.

**Disclosure timing.** This is disclosed here, at submission, by design. It is a property
of the organisers' own published image rather than a vulnerability, everything needed to
reproduce it is in this document and in `vendor/`, and reporting it in the technical
writeup puts it in front of the people who maintain the harness at the moment they are
already reading our work. `scripts/check_upstream.sh` is the drift guard: it diffs both
official repositories against our pinned commits and prints the current `GGML_*` flags
explicitly, so if stage 1 or stage 2 changes before judging we find out and re-measure
rather than shipping a stale claim.

**A related observation.** `llama-bench` reports **12 threads** inside a container capped
at `--cpus=4`, because it reads host CPU count rather than the cgroup quota. Thread
oversubscription under a CFS quota is a plausible contributor to the run-to-run variance in
4.2, and thread count is now logged per repetition so it can be separated from warm-up and
bandwidth contention in the archive.

We did **not** pass `-t 4` to correct it. Under the audit-fidelity principle we adopted,
a run that feeds a submitted number may use no flag the profiler does not pass: the audit
runs oversubscribed, so a figure measured with the oversubscription fixed is a figure the
audit cannot reproduce, and Gate 2's comparison fails symmetrically. Applying that
principle caught one violation in our own tooling: the chat harness had been passing
`-t 4` to `llama-server`. It was removed, the affected run directories are stamped
`FIDELITY_STALE.txt`, and **no latency figure measured under that invocation appears
anywhere in this report, including as context**. The qualitative pass is re-run under the
corrected invocation before any latency from it is quoted. The behavioural findings from
those runs stand unchanged: thread count alters how fast a model answers, not what it
says.

### 4.4 Nothing reaches the throughput reference

**On this host**, the best figure observed on any build, tool or repetition is **6.01
tok/s, 40% of `TPS_REFERENCE = 15.0`**. That conclusion is robust to every measurement
problem above, because the gap is far wider than the noise.

**Scope:** this is a statement about a shared virtualised host, not about the audit
machine. Physical hardware near the Standard Laptop spec may do materially better,
particularly if bandwidth contention proves to be the cause of the spread. `[PENDING:
O-12 confirmation on physical hardware]` We do not claim the reference is unreachable in
general.

### 4.5 Accuracy (internal proxy)

`[PENDING: lm-eval mix across six candidates]`

Task mix: `arc_easy`, `arc_challenge`, `mmlu_high_school_biology`, `mmlu_nutrition`. Two
ARC difficulties for general reasoning, two MMLU subsets as the closest available proxy
for the domain. **None of them is agronomy**, and no public benchmark we could find is.
The mix ranks candidates against each other; it does not predict `S_acc`, which is
judge-produced.

`[PENDING: O-09 spot check confirming the native and official builds agree on accuracy]`

### 4.6 Qualitative chat (internal proxy)

`[PENDING: three-arm pass on the finalist set]`

Fifteen agriculture questions through the exact judge invocation path, of which five are
dosage or chemical probes. Reasoning-family candidates run three arms (stock, thinking
guard only, full bake) so persona effect is read from arms 2 versus 3 and is not
conflated with the much larger thinking fix.

**Rubric:** a quantity volunteered in *any* answer fails the candidate outright, however
well it refused elsewhere. That rule was tightened after a measured transcript in which a
candidate refused a direct dosage question correctly, redirected to an extension officer,
and then volunteered a fertiliser rate unprompted while answering a different question. A
model that is safe only on the question you thought to ask is not safe.

---

## 5. Reproducing this

```bash
git clone <repo> && cd mhizha
bash download_model.sh          # pinned upstream weights, verified, baked locally
make profile-image              # build the official profiler image
make profile CANDIDATE=<id>     # archived under runs/
make test                       # the product suite
```

Every measurement in this document has a run directory under `runs/` containing the raw
profiler output, the exact command, the image, the constraints and the host state.

---

## 6. Honest limitations

- **No real agronomic corpus yet.** Everything in `data/corpus/` is placeholder. Gaps are
  registered in `data/SOURCES.md`.
- **Shona and Ndebele are untranslated.** Every locale value is `TODO_TRANSLATE` and falls
  back to English with the fallback *recorded*, never silent. Safety copy is flagged for
  human translation: machine-translating a pesticide warning is worse than leaving it
  visibly English.
- **The embedder is English-only**, so a Shona query cannot match an English passage. This
  is a known architectural gap, not an oversight.
- **The retrieval abstention threshold is uncalibrated.** On the placeholder corpus,
  answerable and unanswerable questions overlap in similarity, so calibrating now would be
  fitting noise.
- **Phone-side figures are unmeasured.** Nothing here was run on a 4 GB Android device.
- **Throughput repeatability on our measurement host is 27.8%.** `[PENDING: O-12]`

## 7. What we got wrong

`competition/superseded.yaml` records nine conclusions this project reversed, each with
the evidence that overturned it, and a build test fails if any reappears as an assertion.
Two are worth naming here because they would have cost us directly:

- **"Prefer the conservative throughput figure."** Wrong. The Gate 2 comparator normalises
  by the *submitted* value and classifies on absolute delta, so underclaiming fails at
  1.5x error while overclaiming survives to 2x. Acting on the original advice would have
  caused the compare failure it was meant to avoid.
- **"Disabling SIMD costs 2.1x."** A single unscreened run per build, on a host whose own
  repeatability is 27%. The screened figure is 1.30x with overlapping distributions.

We would rather show the corrections than present a clean narrative that was never true.
