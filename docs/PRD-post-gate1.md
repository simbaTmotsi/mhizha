# PRD: What Mhizha should add and change, past Gate 1

**Status:** draft, not yet approved. Nothing in here has been implemented.
**Scope:** the product and Gate 2 path, not the frozen Gate 1 submission. Gate 1 is
submitted (`REPORT.md` status line) and its history is frozen per `SUBMISSION.md`; this
document proposes work that happens *after* that, and touches none of the frozen files
directly.

**Evidence base:** five confirmed ADTC 2026 competitor submissions, checked directly
(Devpost pages, public GitHub repos, and in one case the actual fine-tuning pipeline).
Every competitor claim below is **retrieved**, with its source. See the sources list at
the end. This is not survey opinion; it is what those five repositories actually contain
as of 25 Aug 2026.

---

## 1. The finding this PRD exists to act on

Mhizha shipped a stock model, a chat-template safety bake, and a retrieval layer over a
corpus that is **100% structural placeholder** — by design, per CLAUDE.md rule 4 ("we do
not author agronomic content"). All five confirmed competitors fine-tuned their model on
real agronomic data instead. One of them (AgriLLM / `Agri LLM Compact`) documented the
exact reasoning in its own repo:

> "We first trained on raw `Question:/Answer:` completions, reasoning that the profiler
> scores accuracy through lm-eval's `loglikelihood` path... That was the wrong target.
> The official ADTC FAQ states that S_acc is graded by a judge panel that 'chats with it
> live'... Training every one of 16,000 examples as a single-turn completion taught the
> model a Q&A reflex and measurably degraded its conversational ability."
> — `shem2019/adtc-2026-agrillm`, `train/prepare_data.py`

That is the same conclusion COMPETITION.md section 4 reached (S_acc is judge-produced
through live chat, not the lm-eval self-check). **Mhizha's research was correct. Its
response to that research was not the one that survives contact with a judge.** A judge
who asks a real agronomy question gets a placeholder banner. AgriLLM's judge gets, on a
real pest-identification example quoted in their writeup, the correct answer
(*Spodoptera frugiperda*, fall armyworm) where their own unfinetuned base model said
"maize weevil."

This PRD's central proposal is **not** "abandon the placeholder-corpus principle." It is
"trigger the fine-tuning path CLAUDE.md and COMPETITION.md already wrote the rules for,
using named real sources, under the constraints those documents already specify."

---

## 2. Goals

- Close the gap between "the corpus is honest" and "the corpus can answer anything real,"
  for a bounded, real, sourced slice of agronomy — not all of it.
- Do this without violating rule 4 (no invented facts) or rule 3 (dosage/agrochemical
  conservatism) at any point in the pipeline, fine-tuning included.
- Make every claim in `metadata.json` (language scope, African-alpha bonus) demonstrable
  in the one artifact a judge is guaranteed to run: the two submitted `test_prompts`.
- Spend the next block of effort on the artifact judges interact with, not on additional
  process infrastructure. See section 6.

## 3. Non-goals

- Not a Gate 1 resubmission. The tagged, pushed state stays as submitted.
- Not a rewrite of the RAG/safety architecture. Retrieval-then-generate, the dosage gate,
  and the abstention mechanism are sound and are not in question here.
- Not a push to translate all of `sn.yaml`/`nd.yaml` as a side effect of this work. G-10
  is a named, separate gap with its own labour requirement (fluent speakers with
  extension familiarity) and is out of scope unless section 5's decision below chooses it.
- Not a licence-blind content dump. Every source ingested under this PRD needs the same
  `source`/`publisher`/`refresh_date` discipline `corpus/schema.py` already enforces, plus
  a licence line in `CITATIONS.md`.

---

## 4. Work items

Each item names the subagent already scoped for it in `.claude/agents/`, so this reads as
dispatchable rather than as prose.

### P0 — WI-1: Source and ingest a bounded real corpus

**Owner:** `corpus-curator`.
**Problem:** G-01 through G-07 are all `UNSOURCED`. Nothing in `data/corpus/` is real.
**Proposal:** Pick **one crop (maize) and one province (Mashonaland Central, since it is
already the placeholder's own example region)** and ingest real, licensed content closing
G-01 (planting calendar), G-03 (pest ID, fall armyworm specifically — it is both
candidates' own worked example and the highest-risk category), and G-04 (fertiliser,
**rates excluded** — G-06 must close first, per rule 3, before any rate is servable).
Named sources, retrieved from competitor disclosure rather than assumed:

| Source | What it gives | Licence check needed |
|---|---|---|
| FAO knowledge repositories / ECHOcommunity | Crop and pest manuals | per document |
| CGIAR / CIMMYT Zimbabwe / IITA / ILRI | Africa-specific varieties, pests, practices | per document |
| AGRITEX Zimbabwe extension handbooks | Exactly the register the product needs | often PDF, needs extraction |
| CABI Plantwise factsheets | Pest and disease identification, maps directly to `test_prompts` tp_002 | per document |

**Acceptance:** at least one region/crop pair returns a non-placeholder, cited, human-
reviewed (`review_ledger.jsonl`) answer to a question shaped like the existing
`test_prompts`. `data/SOURCES.md` G-01, G-03 move from `UNSOURCED` to `SOURCED` with the
retrieved document and its licence recorded.

### P0 — WI-2: Trigger the QLoRA proposal COMPETITION.md section 10 already specifies

**Owner:** `model-integrator`, with `agronomy-evaluator` gating the safety-behaviour data.
**Problem:** Section 10's trigger ("stock candidates failing basic agronomy chat") was
never formally evaluated against Gate 1's own qualitative pass, because the pass measured
safety behaviour on a placeholder corpus, not knowledge quality — the trigger condition
was structurally unobservable under Gate 1's own setup.
**Proposal:** Write the minimal QLoRA proposal section 10 requires, for approval, before
any tuning starts:
- existing open datasets only, named with licences (WI-1's sourced content, once reviewed)
- safety-behaviour examples: refusal and redirection on dosage questions, which is the
  behaviour most likely to need reinforcement
- **no invented agronomic facts** — rules out synthesising instruction data, matching WI-1
- **train in chat format, not raw completion.** AgriLLM's own repo documents this exact
  mistake and its correction (quoted in section 1): completion-only training measurably
  degrades conversational quality, which is what the live judge session actually tests.
  This is the one piece of their recipe worth importing verbatim.
- stated time cost and the fluency-degradation risk, per section 10's existing template
**Acceptance:** a written proposal, in the shape section 10 already specifies, submitted
for approval. **This work item stops at the proposal. No tuning starts without a
separate, explicit go-ahead** — same gate section 10 already set.

### P0 — WI-3: Make the language claim demonstrable, or narrow it

**Owner:** `app-engineer` (the metadata/test-prompt surface) plus a decision from Simba.
**Problem:** `metadata.json` claims `language_scope: ["en", "sn", "nd"]` and
`african_alpha_claim: true`, but both submitted `test_prompts` are English, and `sn`/`nd`
are non-functional (`TODO_TRANSLATE` throughout). ARIS's own submission demonstrates the
opposite discipline: one of its two `test_prompts` is written entirely in the claimed
language (Nigerian Pidgin), so the claim is exercised in the one artifact a judge is
guaranteed to run.
**This is a decision, not a default — two paths, both legitimate:**

- **(a) Invest in WI covering G-10/G-11** (translation plus the agronomic term list for
  cross-language retrieval) far enough that one `test_prompt` can genuinely be written in
  Shona or Ndebele and answered correctly. Real labour cost: fluent speakers with
  extension familiarity, per G-10's own stated requirement.
- **(b) Narrow the metadata claim now** to `language_scope: ["en"]` and re-evaluate
  `african_alpha_claim` against what *is* real (the Zimbabwe-specific region filter and
  corpus design), rather than the language seam. Both AgriLLM's and Mhizha's own standing
  rule 5 independently arrive at the same principle: *"an unsupported claim is worse than
  a narrower honest one."* This path costs nothing but honesty and is available today.

**Recommendation:** (b) now, (a) as a tracked follow-on gated on G-10/G-11 closing. Do not
leave the claim standing unexercised into a Gate 2 audit.
**Acceptance:** either a real non-English `test_prompt` that the model answers correctly,
or a `metadata.json` claim that matches what ships, with the change recorded in
`COMPETITION.md`'s decision log the way every other reversal here already is.

### P1 — WI-4: Populate `data/SOURCES.md` with named sources, not just named gaps

**Owner:** `corpus-curator`.
**Problem:** Every gap row names an *institution* ("AGRITEX", "CIMMYT Zimbabwe") but not a
retrievable document or URL. WI-1 will surface real ones for maize/Mashonaland Central;
this item is the general practice of writing them back into the gap register as they are
found, even for gaps not yet closed, so the next session does not re-discover them.
**Acceptance:** at least G-01 through G-07 carry either a real source or an explicit "no
public source found as of [date]" note, replacing bare "UNSOURCED."

### P1 — WI-5: Calibrate the abstention threshold once WI-1 lands

**Problem:** G-14 is explicitly blocked on G-01 through G-07. It has no other
dependencies once WI-1 closes even one crop/region pair.
**Owner:** `rag-engineer`.
**Acceptance:** `retrieval.abstain_below` recalibrated against a corpus that has at least
one real answerable case and one real unanswerable case, replacing the current placeholder
calibration (0.463 vs 0.487, which does not separate).

### P2 — WI-6: A short, separate narrative artifact for non-technical readers

**Owner:** `app-engineer` / whoever writes the next Devpost-style submission.
**Problem:** Several competitors ship a `DEVPOST_STORY.md` distinct from their technical
`REPORT.md` — a short, personal, non-technical narrative for the audience that reads a
project gallery rather than a measurement report. Mhizha's `REPORT.md` is comprehensive
but is not written for that reader, and `README.md` carries the summary today.
**Acceptance:** a short (under 400 words) story-form artifact exists, kept separate from
`REPORT.md` so the figure-provenance rule (COMPETITION.md 9h) never has to apply to prose
that was never meant to carry a citable number.

### P2 — WI-7: Resource-allocation note, not a work item

Two of five confirmed competitors published **only** the six required submission files —
no training code, no dataset, no measurement harness — with the actual engineering done
privately. One (Kuza AI) appears to have submitted the **unmodified official template**
as its linked repo. This is not a recommendation to reduce Mhizha's measurement rigor,
which produced a genuinely defensible, externally-checkable Gate 1 submission and should
stay. It **is** a note for whoever plans the next block of work: the judged surface area
is small (an artifact plus two chat turns), and further investment in process
infrastructure has a lower conversion rate to score than the same effort spent on WI-1 and
WI-2. Weight future effort accordingly.

---

## 5. Explicit non-negotiables (unchanged by this PRD)

- CLAUDE.md rule 1 (fully offline at inference): fine-tuning and corpus ingestion stay
  build-time only, exactly as `src/mhizha/corpus/` already requires.
- CLAUDE.md rule 3 (dosage conservatism): no fine-tuning example teaches the model a rate.
  WI-2 is explicit about this; `tests/test_safety.py` is the enforcement layer and is not
  touched by this PRD.
- CLAUDE.md rule 4 (no invented content): every corpus row and every fine-tuning example
  traces to a named, licensed, dated source. This is the constraint that makes WI-1 and
  WI-2 different from what "just add more training data" would otherwise mean.
- `data/review_ledger.jsonl` sign-off: nothing WI-1 ingests is servable outside a
  development profile until a named human reviewer signs it, exactly as today.

## 6. Open questions for Simba

1. Is this PRD scoped at Gate 2, or at the ongoing product independent of the
   competition? The two have different deadlines and different audiences for WI-6.
2. WI-3's fork: narrow the language claim now, or commit real translation labour first?
3. Who reviews and signs WI-1's ingested content? G-01 through G-07 all name an
   institution, not a person; `review_ledger.jsonl` needs an actual reviewer.
4. Does WI-2's proposal, once written, get approved? Section 10 stops at the proposal by
   design — this PRD does not pre-approve the fine-tune itself.

---

## Sources

- [Agritgllm](https://devpost.com/software/agritgllm) · [repo](https://github.com/bit-collab/adtc-2026-agritgllm)
- [ARIS](https://devpost.com/software/agrigemma) · [repo](https://github.com/Vicgrace01/ADTC-2026-Submission)
- [FarmGate](https://devpost.com/software/farmgate-ja1dm2)
- [Kuza AI](https://devpost.com/software/kuza-ai) · [repo](https://github.com/sudouserx/adtc-2026-submission-template)
- [AgriLLM](https://devpost.com/software/agrillm) · [repo](https://github.com/shem2019/adtc-2026-agrillm), specifically `FINETUNE.md`, `DEVPOST_STORY.md`, and `train/prepare_data.py`, retrieved 25 Aug 2026
