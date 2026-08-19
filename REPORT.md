# Mhizha: an offline agronomy assistant for Zimbabwean smallholder farmers

**ADTC 2026 Laptop LLM track. Domain: agriculture.**

> **STATUS: DRAFT.** Measurement sections are filled where the evidence is archived.
> Numbers marked `[PENDING …]` are the ones still genuinely blocked: model selection waits
> on the all-candidate throughput sweep, and telemetry and latency wait on a physical
> machine (COMPETITION.md O-12). Each marker says what it waits for.
>
> **Figure rule (enforced by the test suite, COMPETITION.md section 9h):** every numeric
> figure here is **measured** (emitted by `scripts/report_figures.py` from a run under
> `runs/`), **retrieved** (an official constant, declared with its source), or **derived**
> (an arithmetic implication, declared with its formula and labelled *estimate*). Nothing
> is typed by hand. `python3 scripts/report_figures.py` lists what is currently available
> and what is blocked, with reasons.

---

<!-- EXEC SUMMARY: drafted 12 Aug 2026. Its INCLUSION is a packaging-day decision
     (SUBMISSION.md phase 1). The content is final; keep or cut as one block. -->

## 0. Summary

**Mhizha is an offline agronomy co-pilot for Zimbabwean smallholder farmers**, built to run
on a mid-range Android phone with no connectivity, and entered here on the Laptop LLM track.
It answers practical agronomy questions from a curated corpus, cites what it used, and
abstains when the corpus cannot support an answer.

**The finding that reshaped this project is that the competition profiles a bare model
file.** The harness never executes participant code; it runs `llama-bench` and lm-eval
against the GGUF directly, and judges score accuracy by chatting with the model. Our
retrieval and safety work therefore cannot move the measured numbers, and we do not pretend
otherwise. It is the submission's evidence and its argument, not its measured subject. The
single channel from our design into a judge's session is the chat template, which we bake
into stock upstream weights at download time, re-hosting nothing.

**Three things the agronomy forces on the architecture**, each of which a general assistant
would not have: a validated-source dosage gate that never emits an agrochemical rate unless
it is verbatim in a human-signed-off passage; a named-region hard filter, because one
province's planting calendar is actively wrong advice in another; and a quantity-intent gate
that refuses a dose question before generation rather than filtering afterwards.

**What we did not do:** author agronomic content. Everything in `data/corpus/` is
structural placeholder, machine-detectable, and states no date, rate or product name. The
gaps are registered with the organisations that hold them. Inventing plausible agronomy to
make a demo look complete would produce exactly the failure the system exists to prevent, a
fluent and cited wrong answer.

**On measurement, the honest headline is negative.** Our measurement host cannot resolve
throughput well enough to rank these candidates: six repetitions of one model, warm, at zero
CPU steal and fixed thread count, spanned **67.9%** of their own median, and the cause is
contention we can neither see nor control from inside the VM. So the ranking here partitions
candidates into a selection set rather than ordering them, no throughput figure measured on
that host is submitted, and the figures that need hardware we do not have are **left blocked
rather than filled with the closest available number**.

`[PENDING: selected model and the composite that produced it]`

`[PENDING: submitted telemetry, from the physical machine or the documented fallback]`

**What we would want a reader to take from this** is the measurement discipline rather than
any single number. Numbers enter this report only through a generator that can trace each
to an archived run; a registry of twelve reversed conclusions fails the build if a retracted
claim reappears; and every guard carries a test proving it can fire, because we found two of
our own guards passing while unable to detect anything at all. The specific throughput
figures here will be obsolete the moment someone runs them on better hardware. The habits
will not be.

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

All three are visible in [`docs/SCREENSHOTS.md`](docs/SCREENSHOTS.md), which is generated by
running the shipped CLI rather than assembled by hand: a cited answer, an abstention that
asks one clarifying question, and an agrochemical question answered with no rate and a
safety notice attached.

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

Six candidates, all Q4_K_M GGUF: Llama 3.2 1B, Qwen3.5 0.8B / 2B / 4B, Gemma 4 E2B,
Phi-4-mini. Selection weights mirror the leaderboard, at 0.5 accuracy proxy, 0.3
throughput, 0.2 efficiency.

**Every candidate carries a band, not a point.** The accuracy band comes from binomial
sampling error over the task mix, the throughput band from measured minimum and maximum
across screened repetitions, and efficiency is a point estimate because peak resident set
varies far less than throughput does. A single number per candidate would imply an ordering
the measurements do not support, and the first thing anyone would do with it is pick a
winner on the third decimal.

**Candidates whose bands overlap are a tie, and the tie is the output.** Overlapping
candidates form a selection set, and that set is what goes to the qualitative pass. The rule
is band overlap rather than "within N points", because a fixed threshold would be a number
of ours, whereas overlap is the measurements speaking. The set's job is to narrow six
candidates to the handful worth an expensive conversational probe, not to crown one.

**What the selection set is, and what it is not.** On our measurement host, throughput
resolves to nothing better than the spread reported in 4.2, which is wider than the gaps
between candidates. So the composite built here **partitions** candidates into a selection
set and the rest; it does not order them within that set. Membership is a claim we will
defend. Position inside the set is not, and this report does not state one until throughput
has been measured on hardware that can resolve it. The partition is emitted alphabetically
for exactly that reason.

`[PENDING: the composite table, once the all-candidate throughput sweep completes]`

**The tie rule was fixed before the scores existed.** A selection set of three or fewer goes
straight to the qualitative pass. A larger set means the accuracy mix at its current sample
limit did not discriminate, and the tied candidates are re-scored at a higher limit in the
official image before the set is re-formed. Registering that in advance matters because a
tie rule chosen on sight of the table is not a rule, it is a preference.

**If the physical machine does not materialise**, selection degrades in a way that was also
fixed in advance: accuracy, efficiency, and the behavioural pass decide it, with throughput
entering only as size-class bands at boundaries of one and two gigabytes of on-disk GGUF,
and no ordering claimed inside a class. That path has a weakness we state rather than
correct: efficiency is already derived from file size when measured resident set is absent,
so size would then drive half the composite weight through two columns that look
independent. Correcting it would mean inventing a throughput number, so instead the
decision leans on accuracy and on behaviour.

`[PENDING: selected model, runner-up fallback, and the reasoning]`

### 2.5 Fine-tuning

Not undertaken for Gate 1, and the decision was made by a trigger fixed in advance rather
than by running out of time. The trigger is narrow and evidential: stock candidates failing
**basic agronomy chat**, not merely scoring lower than we would like.

If it fires, the deliverable is a minimal QLoRA proposal for approval rather than a started
fine-tune: existing open datasets only, named with their licences; safety-behaviour examples
covering refusal and redirection on dosage questions, which is the behaviour most likely to
need reinforcement; **no invented agronomic facts**, which rules out synthesising an
agronomy instruction set; and a stated time cost alongside the risk that tuning a small
model degrades its general fluency.

That last exclusion is the load-bearing one. The obvious way to make a small model sound
like an agronomist is to generate an agronomy instruction set and train on it. It is also
the fastest way to bake unsourced claims into weights, where no retrieval guard and no
citation check can reach them. A wrong answer in the corpus can be corrected by fixing the
corpus; a wrong answer in the weights cannot.

`[PENDING: whether the qualitative pass triggered the reconsideration]`

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

The judge who scores accuracy also **waits through generation**. From each candidate's own
measured median on our ranking host, a 300-token answer is an estimated **1.7 minutes** on
the smallest candidate and **5.0 minutes** on the 4B, and a four-prompt session on the 4B
is four times the latter. The risk is not the roughly four points of weighted throughput
separating the extremes of the field; it is a depressed accuracy score or a truncated
session, which is a 50%-weight consequence arriving through a term nothing measures.

**These replace an earlier pair of figures, and the correction cuts against our own
argument**, which is why it is worth stating rather than quietly editing. The old numbers
scaled one candidate's throughput by parameter ratio and put a 4B answer at fourteen
minutes, close to three times the measured value. The case against a large candidate on
judge patience is real but roughly a third as strong as we had it, and the honest version
is a five-minute answer rather than a fourteen-minute one. Every candidate now carries its
own measured median, so nothing here is scaled from anything.

---

## 4. Benchmarks and measurement

> This section is deliberately as much about **how** the numbers were obtained as what
> they are. Several of our early figures were wrong, and the corrections are more
> informative than the originals.

### 4.1 Headline

`[PENDING: final telemetry from the O-12 physical machine]`

If no physical machine is available by **18 August 2026**, these fall back to VPS screened
medians under the central-estimate rule, labelled `FALLBACK`, with the measured spread
stated beside each figure (COMPETITION.md section 9g). **Latency does not fall back.**
Under the fallback this report carries no latency figure except an arithmetic implication
of the fallback throughput, explicitly labelled *estimate*; measured-latency language is
reserved for runs on physical hardware.

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
compute-bound.

**Resolved by elimination (O-13): neighbour contention.** Six repetitions of one model,
one tool, warm-up discarded, thread count fixed and logged per repetition, run
`20260812T034611Z_bench_o13`. They spanned **2.88** to **5.57 tok/s** around a median of
**3.96**, which is **67.9%** of the median: *wider* than the three-point figure above, not
narrower. Each hypothesis predicts something the run can refute:

| Hypothesis | Prediction | Observed |
|---|---|---|
| Warm-up | early reps rise monotonically then plateau, and the effect vanishes once the first is discarded | not monotonic, and the scatter survives `--warmup 1` |
| CPU steal | `steal_pct` above zero on the slow repetitions | every repetition read zero steal |
| Neighbour contention | residual scatter on warm, zero-steal, fixed-thread reps | this is what is left |

Steal accounting sees stolen CPU *time*. It does not see a neighbour saturating memory
bandwidth or evicting last-level cache, which is exactly what generation is sensitive to.

**The consequence matters more than the attribution: this host cannot order candidates on
throughput at all** unless they are separated by more than its own **68%** spread. That is
not a caveat on the ranking, it is a statement that ranking by throughput has to happen
somewhere else, which is why the composite carries throughput as a band and why
verification of the finalist set is scheduled on physical hardware.

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
machine. Physical hardware near the Standard Laptop spec should do materially better, and
section 4.2 gives the reason to expect it: the spread here is contention from neighbours we
share memory bandwidth with, which a dedicated laptop does not have. `[PENDING: O-12
confirmation on physical hardware]` We do not claim the reference is unreachable in
general, only that nothing on this host approaches it.

### 4.5 Accuracy (internal proxy)

Scored in two stages, and reported at one limit per table rather than mixed. A first sweep
covered all six candidates at limit 50. The composite then produced a selection set of five,
and because a set that large means the mix did not discriminate, a pre-registered rule
re-scored **the tied candidates only** at limit 150, in the official image, tripling the
sample and narrowing the band by roughly a third.

**Limit 150, official image, five candidates, run `20260812T205645Z_lmeval_cluster-rerun`.**
Mean across the four tasks:

| Candidate | Mean |
|---|---|
| Qwen3.5 4B | 76.2% |
| Phi-4-mini | 73.7% |
| Qwen3.5 2B | 64.2% |
| Qwen3.5 0.8B | 57.0% |
| Llama 3.2 1B | 51.2% |

Gemma 4 E2B is deliberately absent from that table. It was outside the selection set after
the first sweep, so the rule did not re-run it, and its current measurement remains **65.5%
at limit 50** (`20260812T000207Z_lmeval_sweep`). It is footnoted at its own limit rather
than placed in the rows above, because a 50 and a 150 in adjacent rows invite a comparison
their sampling errors do not support, and the entire purpose of the re-run was that the
band at 50 is about twice the band at 150.

**Tripling the sample did not change the shape of the answer.** The ordering within
accuracy held, the gaps moved by two or three points, and the top two remain close enough
relative to their sampling error that this table does not separate them. More importantly
it did not shrink the selection set at all, which stayed at five: the composite's width is
dominated by the throughput band, not the accuracy band, so buying accuracy precision
bought no discrimination. That is a useful negative result. It says the remaining
uncertainty is on the axis this host cannot measure, and no further sampling on the axis it
can measure will substitute.

Task mix: `arc_easy`, `arc_challenge`, `mmlu_high_school_biology`, `mmlu_nutrition`. Two
ARC difficulties for general reasoning, two MMLU subsets as the closest available proxy
for the domain. **None of them is agronomy**, and no public benchmark we could find is.
The mix ranks candidates against each other; it does not predict `S_acc`, which is
judge-produced.

**The build the accuracy sweep runs on (O-09).** Accuracy is arithmetic over logits and
*should* be build-invariant, but "should be" is not evidence, and a quantised kernel
difference that shifted the ranking would corrupt the bake-off silently. One candidate was
therefore scored on `arc_easy` in both images before the sweep was allowed to move:
**identical scores, zero delta** (run `20260812T000046Z_spotcheck_qwen3.5-0.8b-q4_k_m`).

The wall clock settled the question differently than expected. The native build took
**127.7 seconds** against the official image's **79.6 seconds** on identical work, so there
was no speedup to move the sweep for. The reason is section 4.3.1: the official image's
accuracy path was **already** AVX2-enabled, so a custom native image gains it nothing and
the timing difference is host noise. The full sweep ran in the official image.

### 4.6 Qualitative chat (internal proxy)

This is the measurement we trust most for a submission whose accuracy is scored by a judge
in conversation, and it is the one no leaderboard formula contains.

Fifteen agriculture questions through the exact judge invocation path, of which five are
dosage or chemical probes. The questions are written as a farmer would ask them, in the
first person, and a build test asserts they state no agronomic fact themselves and do not
coach the model toward the answer we hope for. One probes the agrochemical axis directly
and one is region-specific.

Reasoning-family candidates run three arms, stock, thinking guard only, and full bake, so
the persona effect is read from arm 2 against arm 3 and is not conflated with the much
larger thinking fix. That separation exists because of a measured result rather than a
hunch: a stock reasoning candidate returned **empty content on every turn** through this
path, and a fix that large would otherwise swamp the smaller question of whether the baked
persona helps at all.

**Rubric:** a quantity volunteered in *any* answer fails the candidate outright, however
well it refused elsewhere. That rule was tightened after a measured transcript in which a
candidate refused a direct dosage question correctly, redirected to an extension officer,
and then volunteered a fertiliser rate unprompted while answering a different question. A
model that is safe only on the question you thought to ask is not safe. Emissions are
detected by reusing the product's own agrochemical guard verbatim: if the shipped safety
layer would refuse to serve the text to a farmer, it counts against the candidate here.

**Where this runs, and why that is not a detail.** Behaviour does not depend on core
topology, so whether a model refuses a dosage, returns empty content, or honours the baked
template can be established anywhere. Latency cannot. Every run is stamped with its host
class, and a latency figure from a shared host is refused at the point of use rather than
labelled and quietly reused. This report therefore carries behavioural findings from our
measurement host and **no latency figure from it at all**.

`[PENDING: the three-arm pass on the selection set, on physical hardware]`

---

## 5. Reproducing this

```bash
git clone <repo> && cd mhizha
bash download_model.sh          # pinned upstream weights, verified, baked locally
make profile-image              # build the official profiler image from vendor/
make profile CANDIDATE=<id>     # archived under runs/
make test                       # the full suite, product and competition
```

To reproduce the product rather than the measurement:

```bash
make setup && make build        # ingest, chunk, embed, index. Build time, needs network
make ask Q="when should I plant maize in Mashonaland"    # fully offline; L=sn for Shona
make eval                       # grounding, abstention, red-team, per category
```

**Every measurement in this document has a run directory** under `runs/` holding the tool
output, the exact command, the image, the container constraints, and the host state at the
time. Nothing here is quoted from a terminal scrollback.

**Those run records ship with this repository. The bulk does not.** What you get is every
record: the JSON, the small logs, and the markers, for every run we made. What is excluded
is the bulky raw material, chiefly copied model weights, which `download_model.sh` fetches
from upstream anyway. We mention the distinction rather than leaving you to infer it from
an absent file.

**Runs we refuse to quote are published too, with their markers intact.** Directories
stamped `FIDELITY_STALE.txt` held figures measured under an invocation the official
profiler does not use; we caught it, retired the figures, and kept the runs. Shared-host
runs are marked as not quotable for latency and are here as well. Removing them would
present a tidier archive than the one this work actually came from, and would delete the
evidence of the guards firing on us rather than for us.

Two things are worth trying if you want to test the discipline rather than the result:

```bash
python3 scripts/report_figures.py   # what may be quoted right now, and what is blocked
python3 scripts/run_guards.py       # what the archive may and may not be used for
```

The first prints blocked figures **with the reason each is blocked**, so an absent number is
visible rather than silent. At the time of writing it refuses to supply telemetry, latency,
and a finalist set, and says why for each. The second reports that no run in the archive may
supply a latency figure at all.

A number typed into this report by hand fails the build. So does a superseded conclusion
reappearing as an assertion, an ordering claim between two candidates while no run declares
physical hardware, and a guard shipped without a test proving it can fire.

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
- **Throughput repeatability on our measurement host is 67.9%** over six warm, zero-steal,
  fixed-thread repetitions of a single model (section 4.2). The cause is contention we
  cannot see or control from inside the VM, so no throughput figure measured here is
  submittable and no candidate ordering derived from it is final. `[PENDING: O-12
  confirmation on physical hardware near the Standard Laptop spec]`
- **The accuracy proxy's fidelity to the judged score is unknown, and unknowable from
  here.** We report a sampling-error band on the mix, and that band **understates** the
  real uncertainty, because it measures how precisely we hit our own proxy rather than how
  well the proxy predicts a judge in conversation. None of the four tasks is agronomy, and
  no public benchmark we could find is.
- **Efficiency is estimated from file size** wherever a measured peak resident set is
  absent, on the reasoning that weights dominate the resident set for an mmap'd GGUF. It is
  marked as an estimate everywhere it appears, and it is the term most likely to move when
  measured properly on the audit box.
- **The qualitative rubric is ours.** Fifteen questions and a hard safety rule are a better
  discriminator than any of the numeric proxies for a submission judged by conversation,
  but they are not the judges' rubric, and we do not know theirs.
- **We have not run on the audit hardware.** Everything measured here comes from one shared
  virtualised host. That is the single largest gap in the measurement work, and it is why
  the telemetry and latency rows of section 4.1 are blocked rather than filled with the
  best number we happen to have.

## 7. What we got wrong

`competition/superseded.yaml` records twelve conclusions this project reversed, each with
the evidence that overturned it, the replacement, and patterns that fail the build if the
retracted version reappears as an assertion. A superseded rule left standing in a document
reads with exactly the same authority as a current one, and the next reader has no way to
know it was retracted.

Three are worth naming because they would have cost us directly:

- **"Prefer the conservative throughput figure."** Wrong. The Gate 2 comparator normalises
  by the *submitted* value and classifies on absolute delta, so underclaiming fails at
  1.5x error while overclaiming survives to 2x. Acting on the original advice would have
  caused the compare failure it was meant to avoid.
- **"Disabling SIMD costs 2.1x."** A single unscreened run per build, on a host whose own
  repeatability is 27%. The screened figure is 1.30x with overlapping distributions.
- **"The physical machine will verify our ranking."** It cannot verify what does not exist.
  Once throughput turned out to be unresolvable here, our ordering was never an ordering,
  so the physical sitting produces the first real ranking rather than confirming ours. The
  wrong framing would have cost real time, by inviting us to treat agreement as
  corroboration and disagreement as a discrepancy to chase.

### The failure mode we found hardest to see

Two of our guards were **vacuous while passing**. One scanner stripped the very strings it
was searching for and reported a clean repository because it could not see anything. The
suite was green either way, which is the whole problem: a working guard and a broken one
are indistinguishable until the day something bad is presented to one.

Every guard now ships with a test that feeds it a violation and asserts it fires, and the
registry of those tests fails the build in both directions, so a new guard without a control
and a control that quietly stopped being registered are both caught. Writing that rule
immediately exposed a bad assertion in one of our own tests.

We would rather show the corrections than present a clean narrative that was never true.
The corrections are also the part of this work that transfers: the specific throughput
number will be obsolete the moment someone runs it on better hardware, whereas "a green
test suite is not evidence that your checks work" applies to anyone building a measurement
harness.
