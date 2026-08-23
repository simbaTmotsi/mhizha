## Inspiration

A farmer in Mashonaland is deciding what to plant this week. The nearest AGRITEX extension
officer is a bus ride away, and there is no signal in the field. An assistant that needs a
network is not there at the moment the decision actually gets made.

That much is the obvious problem. The one that shaped the whole build is less obvious:
**for this user, the dangerous failure is not unhelpfulness. It is confidence.** A chatbot
that declines to answer wastes a trip. A chatbot that invents a cypermethrin mixing rate
destroys a season, or harms the person holding the sprayer. Agrochemical dosages, pre-harvest
intervals and re-entry periods are exactly the kind of specific, plausible-sounding numbers
a language model is happiest to produce and least able to be trusted on.

So Mhizha is built to refuse. **A dose that is not written, word for word, in a retrieved
passage a human has signed off is never emitted** — not as an estimate, not as a typical
figure, not when pressed, not when told it is urgent.

## What it does

Mhizha runs entirely offline on a mid-range Android phone. A question goes through language
detection, a local sentence embedder, and top-k retrieval from a single SQLite file. Then:

- **Below a confidence threshold, the model is never called at all.** It abstains, asks the
  one clarifying question that would unblock it, and refers the farmer to their local
  extension officer.
- **Every answer cites its passages** with source, publisher and refresh date, so it is
  defensible to an extension officer rather than merely fluent.
- **A quantity-intent gate fires before generation**, not after, on a trigger list of
  agrochemical terms.
- **Shona and Ndebele are a seam in the architecture**, carried through the locale layer and
  the retrieval path, rather than a translation pass bolted on at the end.

`make eval` currently reports grounding 4/4, red-team 16/16, **no critical failures**.

## How we built it

The competition profiles a **bare GGUF**, not our code. The profiler loads the model file
directly, so none of the stack above runs while judges are scoring. That single fact
reorganised the whole submission: the only channel from our work into a judge's session is
**the chat template embedded in the model file**, which we bake at download time. Our safety
posture ships as text inside the artefact the organisers actually run.

Reading the profiler's own source told us what we were optimising against:

$$S_{\text{perf}} = \min\!\left(\frac{\text{TPS}}{15.0},\ 1\right)\times 100
\qquad
S_{\text{eff}} = \max\!\left(0,\ \frac{7.0 - \text{peak RSS}_{\text{GB}}}{7.0}\right)\times 100$$

Two things fell out of that. The reference throughput is a **fixed constant, knowable in
advance**, not a curve against other entrants. And the audit image builds `llama.cpp` with
every x86 vector extension disabled — we measured the same model at **1.82 tok/s** in the
official image against **3.83 tok/s** in an otherwise identical AVX2 build. Throughput was
close to unwinnable for everyone, which meant judge-scored accuracy dominated, which meant
**model selection had to be decided on behaviour rather than on speed**.

So we selected by reading transcripts **candidate-blind**. Arms were labelled A, B, C, the
mapping was sealed, the rubric and the ordering were committed before the seal was opened.
Result: 95 / 93 / 81 out of 96.

**The blind changed the answer.** Our accuracy proxy favoured the 4B model by twelve points,
and it is the larger model — but read blind, the 2B scored higher. The margin is two points
out of ninety-six, which is narrow, and we report it as narrow. It is usable *because* it
was committed before the mapping was opened.

## What we learned

**Throughput was not reproducible, and steal screening did not save us.** Six repetitions of
one model on one host, warm-up discarded, threads fixed, **every single run at 0.00% CPU
steal**, spanned **67.9% of their own median**. Not monotonic, so not warm-up. Zero steal, so
not theft the kernel could see. By elimination: contention on memory bandwidth and cache that
steal accounting simply does not measure. We concluded that our own host could not rank
candidates on throughput at all, and said so in the report instead of publishing an ordering
we did not have.

**A green guard can be a guard that cannot fail.** We found two of our own checks passing
vacuously — one written earlier the same day. Now every guard ships with a test that feeds it
a violation and asserts it fires. Ten guards, ten positive controls, enforced bidirectionally
so an unregistered guard and an unregistered control both fail the build.

**A silent fallback that changes results is indistinguishable from fabrication.** Our setup
installed dependencies and stopped, so a fresh clone had no embedder weights and quietly fell
back to a deterministic hash embedder. Every retrieval result then differed from ours, with
nothing on screen to explain why. A judge reproducing our screenshots would have got different
passages, different scores, a different answer — and the reasonable conclusion from their side
is that we made the screenshots up. The fallback now defaults off and refuses loudly.

**Write down what you got wrong, in a form that fails the build if it comes back.**
`competition/superseded.yaml` holds **13 reversed conclusions**, each with the evidence that
overturned it, and the test suite fails if a retracted claim reappears as an assertion
anywhere in our documents. One of those entries would have caused the exact scoring failure it
was written to avoid.

## Challenges

**We never got audit-class hardware.** Our own dated rule said that if no physical machine
near the Standard Laptop spec existed by 18 August, submitted telemetry falls back to screened
medians on our shared host. It fired. So we submit **3.27 tok/s with 15.0% spread and
1433.78 MB peak RSS, labelled `FALLBACK`**, with the spread printed next to the figure so a
judge sees the uncertainty rather than false precision.

**And the report carries no latency figure at all.** Latency does not fall back. There is no
honest substitute for judge-experienced latency measured on a machine with the judges' core
topology, so rather than publish a number from a shared VPS we published the absence and the
reason. An absent number is recoverable. A wrong one presented as measured is not.

**The corpus is placeholder, and we say so on screen.** We built the ingestion, schema,
validation ledger and retrieval; we did not author agronomic content, and we refused to write
plausible-sounding facts to fill the gaps. Every chunk is flagged `placeholder: true`, every
answer carries a banner saying so, and the fourteen things we still need — and the
organisations that hold them — are registered in `data/SOURCES.md`. A demo that implied real
agronomic content would be precisely the failure the whole system exists to prevent.

## What's next

Fill the corpus with validated content, source by source, each signed off by a named reviewer
in the ledger. Swap in a multilingual embedder so a Shona query can match an English passage.
And run the physical sitting we never got, which turns the fallback telemetry into a measured
number and makes latency quotable for the first time.

---

**328 tests pass.** The full method, including everything above that went wrong, is at
[github.com/simbaTmotsi/mhizha](https://github.com/simbaTmotsi/mhizha) — `REPORT.md` for the
submission, `COMPETITION.md` for the working record.
