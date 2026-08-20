# HANDOFF

Written 12 Aug 2026, updated 12 Aug ~08:40Z. **Read `COMPETITION.md` first**: it is the
source of truth and this file only points into it.

---

## Read these, in order

0. **`SUBMISSION.md`** if it is 20 August or later. It is the ordered packaging-day
   runbook and it supersedes any recollection of what order things happen in.
1. **`COMPETITION.md`** (~1500 lines). Sections 9a to 9h are the recent working decisions.
   Section 13 is the open-items table.
2. **`competition/superseded.yaml`** (11 entries). Conclusions this project has **reversed**,
   each with the evidence that overturned it. `make test` fails if any reappears as an
   assertion. Read this before trusting any recollection of "what we decided".
3. **`docs/BAKEOFF.md`** for candidate state, **`REPORT.md`** for the submission draft.

## Ground truth, briefly

The competition scores a **bare GGUF**, not our code. The profiler runs `llama-bench` for
throughput and lm-eval for accuracy against the model file directly; `S_acc` is produced by
**judges chatting with the live model**. Our RAG/safety stack is the story and the
evidence, not the measured subject. The only channel from our work into a judge's session
is the GGUF's embedded chat template, which we bake at download time.

The product path (offline agronomy assistant, 4 GB phone) is **untouched and green**:
300 tests pass, red-team eval 100%, no critical failures.

---

## What changed on 12 Aug (~08:20 to 08:40Z)

No new measurement was taken: the bench sweep owns the CPU, and adding load to a host whose
whole problem is unaccounted contention would corrupt the thing being measured. The suite
was run twice, niced, in windows 08:35:52-08:36:03Z and 08:37:10-08:37:19Z; if a repetition
in those windows looks odd, that is why. **302 tests pass, 1 xfail** (the O-02 placeholder
guard, as intended).

- **The artefact composite can no longer reach the report.** `report_figures.py` published
  `composite.finalists` without ever reading `ranking_complete`, so the finalist set of one
  was one hand-copy away from `REPORT.md`, reading exactly like a real result. It is now
  refused with the unranked candidates named, matching how latency and telemetry are
  already refused consumer-side. Two tests cover it: a partial table publishes nothing, a
  complete one still publishes.
- **`REPORT.md` 4.5 filled**: the six-candidate accuracy proxy, read as three pairs rather
  than six places, plus O-09's outcome.
- **`REPORT.md` 4.2 filled**: O-13's resolution as an elimination table, and the point that
  matters more than the attribution, which is that this host cannot order candidates on
  throughput at all.
- **O-09 and O-13 marked closed** in the section 13 table with their run ids. Both were
  still listed open while their evidence sat in the archive.
- **`CITATIONS.md` written.** Every third-party licence claim is marked *retrieved* with a
  date or *unverified*, because this project has already been wrong about one (SR-04).
  Section 6 states plainly that no agronomic content is attributed because none was used.
- **`README.md`**: an ADTC section with the judge-facing reproduction path; the stale
  "174 tests" count dropped rather than re-pinned.
- **`docs/BAKEOFF.md`**: accuracy results recorded, and the artefact composite fenced off.

Then, in a second pass on the same day:

- **One door onto the measurement archive.** `run_guards.py` gained typed access:
  `Measurement` carries its run id, `Absent` refuses to be a number at all. `composite.py`,
  `report_figures.py` and `ab_template.py` no longer open `runs/`, parse a record, or hold
  their own `RUNS`. Two tests: one greps consumers, one proves the grep can fail against
  the shape of the code that existed before.
- **9f-bis pre-registered at 08:55:09Z**, while the sweep was in round 1 of 4 with five
  candidates unmeasured. The VPS composite is provisional *by construction*; the physical
  sitting completes the ranking rather than verifying it; and the degraded selection path
  is fixed in advance for 18 Aug. **SR-12** forbids the verification framing coming back.
- **The sitting is budgeted and ordered** (section 9g), including the ordering that keeps
  an overrun from costing the audited number, and a pre-registered cut with a registered
  default (**O-15** carries the deferred persona question).
- **Provisional tables partition rather than rank**, in the record, in the printed table,
  and in prose: a doc-regression check refuses candidate-ordering language in `REPORT.md`
  and `docs/BAKEOFF.md` while no run declares `host_class: physical`. Writing it caught a
  legitimate across-class claim in `BAKEOFF.md` resting on parameter-count arithmetic, so
  the rule exempts claims that state their basis, the same way the superseded registry
  exempts a forbidden phrase near a correction marker.
- **Section 12b, the positive-control rule.** Every guard now has a test that feeds it a
  violation. Two guards here were vacuous while green, including one written earlier the
  same day, which is why the rule exists rather than the habit.

**The guard layer is frozen as of 12 Aug.** New guards only on a demonstrated failure,
never on anticipation. There are nine, each with a positive control, and that is enough.
Effort now goes to machine-independent submission artifacts, which is everything that does
not need the O-12 machine.

Third pass, same day:

- **`REPORT.md` prose is complete except for blocked figures.** Sections 2.4, 2.5, 4.6, 5,
  6 and 7 are written out: the selection *method* including the partition rule and the
  degraded path, the fine-tuning trigger and why an invented agronomy instruction set is
  excluded, the qualitative protocol, a fuller reproduction section, four limitations that
  were missing (proxy fidelity, estimated efficiency, our own rubric, no audit hardware),
  and the vacuous-guard lesson. Only figure slots remain `[PENDING]`.
- **CLI captures are generated, not pasted.** `make captures` runs the shipped entry point
  and writes `docs/screenshots/*.txt` and matching SVGs, plus `docs/SCREENSHOTS.md`. Four
  paths: cited answer, abstention, agrochemical refusal, device budget. Re-runnable and
  diffable, so an asset cannot outlive the behaviour it claims.
- **`docs/VIDEO.md`**: the 2-minute script skeleton, beat-timed to 1:55, with the rule that
  no figure is spoken unless it is already in `REPORT.md` under 9h, and that an unavailable
  figure means the sentence is cut rather than softened.
- **Section 9h gained a note**, at your instruction: a stated basis containing a number
  carries its own 9h provenance. An exemption in one guard is not an exemption in another.
  Verified, and its two boundaries are written down (unitless quantities, and BAKEOFF.md
  not being scanned) so the coverage is not overstated. Recorded only, nothing built.
- **`SUBMISSION.md`**, the packaging-day runbook: go/no-go, content freeze, the 22 Aug
  upstream gate, the repo flip verified from a fresh clone, video upload, the Devpost form.
  Ordered by dependency, with the reasoning for the order, because each phase either feeds
  the next or gates whether it is still valid. Its phase 1.2 is the recorded compensating
  control for `BAKEOFF.md` sitting outside the figure rule: one hand-check on the day,
  looking first for a number that contradicts `REPORT.md`. Not a scanner, by decision.

  Writing it surfaced three things worth knowing before the day, two now resolved: the
  template asks for a one-to-three-page report and ours is far longer, and `metadata.json`
  still names the artefact candidate rather than a chosen one.

Fifth pass, two report fixes before freeze:

- **Removed a duplicated rubric paragraph** in `REPORT.md` section 4.6, left behind when
  the section was expanded.
- **Recomputed every answer-time figure from measured medians.** `REPORT.md` section 3 and
  the `docs/BAKEOFF.md` structural-points table were both built on one candidate's
  throughput scaled by parameter count. Measured, a 300-token answer on the 4B is **5.0
  minutes, not 14**, and a four-prompt session is about 20 minutes rather than close to an
  hour. **The correction cuts against an argument we liked**: judge patience is still the
  strongest reason to prefer a small candidate, but roughly a third as strong as we had it,
  and the old figure would have justified excluding candidates it does not exclude. Both
  documents keep the retracted numbers visible rather than quietly editing them.

  The old constant was wrong twice: its recorded formula, `300 / (4.29 / 5) / 60`,
  evaluates to 5.8 and not to the 14 it was filed under, because the divisor actually used
  was 12. Nothing recomputes `report_constants.yaml`, so derived entries are hand-checked
  when their inputs move. That is now written at the top of the `derived_latency` block.

Fourth pass, on your rulings:

- **`runs/` ships as records, not bulk.** `.gitignore` now publishes every record (58
  files, under half a MB) and keeps the bulk out. **Not-for-quotation runs ship too, markers
  intact**, including every `FIDELITY_STALE` directory: they are the evidence the guards
  fired on us, and an archive with them removed would be cleaner than the one we worked
  from. `REPORT.md` section 5 states records-not-bulk explicitly rather than leaving a
  reader to infer it from an absent file.
- **`scripts/scrub_runs.py`**, run at phase 3.2 **before the first `git add`**, because git
  history is not scrubbable afterwards and `runs/` has never been committed. It rewrites
  this repo's absolute path to a relative one (lossless) and *flags without rewriting*
  home directories, hostnames, IPs and provider names, since a wrong automatic substitution
  inside an archived record is worse than a flagged one. Current state: 9 files to rewrite,
  nothing flagged. It deliberately keeps `cpu_model`, `ram_gb`, `host_cpu_count` and steal
  readings, and prints that list every run, because the oversubscription finding cannot be
  stated without `host_cpu_count`.
- **The producers now write repo-relative paths** (`judge_chat.py`, `composite.py`), so the
  scrub is a safety net rather than a recurring chore. It still must be re-run on the day.
- **`REPORT.md` section 0 is the executive summary**, drafted with its figure slots and
  marked in the source with an `EXEC SUMMARY` comment. Only its **inclusion** is a
  packaging-day call: keep or cut as one block, never part-edit.
- **The `african_alpha` defence is written**, one sentence in design tense, in `SUBMISSION.md`
  phase 1.3. Every clause names something that exists in the repo, which is the test of
  whether the claim is load bearing.
- One guard change, not a new guard: the archive-door test gained a **conditional**
  exemption for text-only tools, asserted by requiring that such a tool parses no JSON at
  all. `scrub_runs.py` reads records as text and never as measurements.

Still true and still worth reading below: the finalist set is not formed, telemetry and
latency are blocked on O-12, and `metadata.json` still holds `TODO_*`.

## State as of 19 August, five days from the deadline

**O-02 is filled.** team_id `mhizha`, Simbarashe Timothy Motsi, simbamotsi1@gmail.com,
GitHub handle `simbaTmotsi` (normalised from a URL: the template asks for a username). The
placeholder test passes rather than xfails, so the suite is **325 passed, 0 xfailed**.

**O-16 is closed: the repository is private, confirmed 20 Aug**, and stays private until the
23rd flip (SUBMISSION.md phase 3). That retires the open question about accidental early
publication.

**The repository is already on GitHub and already pushed.** Five commits, three pushes in
the reflog, local equal to `origin/master`. That overtakes part of phase 3: the flip is now
"is it public, and was it scrubbed", not "does it exist". Consequences below.

**Scrub applied.** `scrub_runs.py --apply` rewrote 9 files; the diff is path prefixes only,
no measurement value touched, verified against a pre-scrub copy. `capture_cli.py` now
relativises the repo path when it makes an asset, because `doctor` prints absolute config,
index and embedder paths and would have regenerated them. The working tree has **no
`/home/` string left outside `vendor/`**.

**What the history audit found, over all five commits.** Exactly one class of identifying
string: the absolute home path, in `docs/SCREENSHOTS.md`, the two `04-doctor` capture files,
and 9 run records. **No email, no token, no key, no hostname, no real IP.** The
`127.0.0.1` hits are loopback in `judge_chat.py`, and the provider names are
`scrub_runs.py`'s own detection pattern. `runs/` **was** already committed and pushed, so
the "one clean moment before the first commit" that the runbook describes has already
passed; the fix is forward, and whether history is rewritten is a judgement call recorded
under the open items rather than a secret to contain.

**Both dated fallbacks have fired**, and the behavioural pass is running.

**18 August passed with no physical machine, so O-12 lapsed.** Two clauses activated on
their own, exactly as designed, without anyone remembering to:

- **9g telemetry fallback is OPEN.** `report_figures.py` now offers telemetry from
  `20260812T072644Z_bench_all-candidates`, stamped `fallback_invoked: true` and labelled
  FALLBACK. Submit the central estimate with its spread beside it.
- **Latency is still BLOCKED**, and stays blocked. Latency never falls back. The report
  carries no latency figure at all, which is the correct outcome, not a gap to fill.
- **9f-bis degraded selection is live**: the finalist is chosen on accuracy, efficiency and
  the behavioural pass, with throughput entering only as size-class bands.

**The cluster re-run finished and did not collapse the cluster.** Limit 150, five
candidates, `20260812T205645Z_lmeval_cluster-rerun`, ~2.5 h per candidate. The composite
re-formed on it is `runs/20260819T163941Z_composite`, and the selection set is **still
five**. Accuracy precision tripled and bought no discrimination, because the composite's
width is dominated by the throughput band, not the accuracy band. That is the empirical
version of the call already recorded here: **the physical bench collapses this set, not
more VPS accuracy.** Do not run a third sweep.

9f-pre's own answer to a set still above three after the re-run is to take the larger set
to the qualitative pass rather than make an arbitrary cut.

**The degraded path was pre-registered at 17:47:40Z and then executed** (section
9f-bis-exec, written before the partition was computed). `composite.py --degraded` recomputes
with throughput as size-class bands only, every member of a class handed the identical band
so the term cannot order them in arithmetic and not merely in prose. Class A `S_perf`
[18.51, 25.01], B [8.82, 17.61], C [5.09, 12.12].

**The degraded partition is also five**, so per the registered rule the larger set runs.
Record: `runs/20260819T174950Z_composite`, `degraded: true` with its basis stored.

**Behavioural pass running since 17:50Z**, `/tmp/behavioural_pass.log`, four candidates in
accuracy-descending order: qwen3.5-4b, phi-4-mini, qwen3.5-2b, llama-3.2-1b. Full 15-question
probe. Roughly eight hours at these rates, so it should land overnight. **Qwen3.5-0.8B is
excluded**: its archived A/B shows one volunteered quantity in the baked arm, which the
amended rubric fails outright, and that stands regardless of composite membership. The
record's own `verdict` field still reads `ship-baked`, which predates the amendment and is
stale; the finding is what stands.

**The selection rule was registered at 17:56:49Z, before a single transcript existed**
(section 9f-bis-sel), with two clarifications registered at 18:01:46Z, still before any
transcript: hard-fails eliminate; survivors order on **`grounded`, `refusal`, `concise`
only**; behavioural ties break to limit-150 accuracy **on the point estimate, not the
band**; and **throughput never breaks a tie**.

**Amended 18:14:43Z, still before any transcript.** The fourth axis is back in the ordering,
renamed **`relevance`** under its unchanged definition, *"answers what was asked"*. The
18:01:46Z strike had argued it was per-turn timing by another name; it never was, and the
strike argued against a definition the rubric does not contain. Both the correction and the
original error are recorded in 9f-bis-sel rather than tidied away.

The worry behind the strike was real and is now handled where it belongs: **score every
transcript through `python3 scripts/score_view.py <run>`**, never `chat.json` directly. It
strips every time-derived field and refuses to emit if one survives. Per-turn seconds stay
in the archive, out of the scorer's sight. Contamination closed at the scorer, signal kept
in the rubric, which is the sibling of unquotable-not-deleted. It handles a chat run or a
whole A/B, rendering arms from `ab.json`'s own rows rather than guessing sibling
directories by name, which would pick the wrong arm for a candidate that has two A/Bs.
This one does.

The point-estimate rule exists because **a tie-break orders after significance has given
up**. By step 3 the bands have already been consulted twice and have already answered "these
overlap". Asking a third time returns the same non-answer. The
runner-up is the next survivor in that order and goes into `config.yaml` beside the winner,
because the 22 Aug upstream check may need it in a hurry. All candidates eliminated is not
a deadlock, it is the section 10 fine-tuning trigger.

When the pass finishes, read **emission counts, not the `verdict` string**, for any run
recorded before the rubric amendment. The stale label on the 0.8b A/B is annotated by
`VERDICT_STALE.txt` **beside** the record, never inside it: editing `verdict` in place would
make the archive disagree with the code that wrote it, and would delete the evidence that a
rule was tightened because a measured transcript showed the old one was insufficient.

**No latency from these runs enters any document**, confirmed 19 Aug. Timings stay in the
records, quotation stays refused, no re-run.

**Presenting the 150 results: no mixed limits in one table.** The five tied candidates are
at 150; gemma-4-e2b is not, because 9f-pre re-runs tied candidates only. So every accuracy
table becomes the five at 150, with **gemma footnoted at 50** and out of the ranked rows.
Two limits in adjacent rows invite a comparison the sampling errors do not support, and the
whole reason for the re-run is that the band at 50 is about twice the band at 150. Applies
to `REPORT.md` section 4.5 and `docs/BAKEOFF.md` alike.

**Expect the cluster to land at three or four, and stop there.** If it does, that is
9f-pre working: straight to the three-arm pass, on the O-12 machine. **Do not spend more
VPS accuracy on it.** What collapses a cluster of three or four is the physical bench,
because the term that cannot separate these candidates is throughput, and no amount of
additional accuracy sampling substitutes for measuring it on hardware that can resolve it.
A third accuracy sweep would be effort spent on the axis that is already the sharpest.

The sweep it replaced, for the record: `bench_screened.py --candidates all --reps 4
--warmup 1`, archived as `runs/20260812T072644Z_bench_all-candidates`, official image, all
six candidates, ~13.5 hours. Medians and spreads are in `docs/BAKEOFF.md`. Its own output
warned that three candidates exceeded 25% spread, which is the O-13 result reproducing at
scale rather than a surprise.

---

## Behavioural pass: adjudicated, 20 Aug

Pass complete 19 Aug 22:12Z. **Step 1 of 9f-bis-sel has been re-adjudicated mechanically
under SR-13, from the archived records. No fate was decided by hand.**

| Candidate | ships | why |
|---|---|---|
| qwen3.5-4b | **baked** | stock degenerate (14/15 empty); baked clean, 5 redirects, 8/10 controls |
| qwen3.5-2b | **baked** | stock degenerate; baked clean, 5 redirects, 9/10 controls |
| phi-4-mini | **baked** | stock volunteered 2 quantities so is ineligible; baked clean |
| llama-3.2-1b | candidate-fail | no eligible arm: stock volunteered 2, baked volunteered 1 |
| qwen3.5-0.8b | candidate-fail | both archived records; pre-amendment record cannot certify eligibility |

**Survivors: qwen3.5-4b, qwen3.5-2b, phi-4-mini.**

**SR-13 settled the arm-scope ambiguity, post-transcript and recorded as such.** Hard-fails
screen artifacts, not diagnostics: per arm, eligible = zero volunteered quantities AND
non-degenerate AND control not killed; stock preferred among eligible arms; a candidate
fails only when no arm is eligible; arm 2 ships never and votes never. The any-arm reading
would have failed all four candidates, because both qwens volunteered 3 quantities each in
a diagnostic arm that never ships.

**Two guard defects were found by running the rule, both now fixed with positive controls.**
The first is the one that prompted this: `decide()` screened the baked arm only, so it
recommended shipping phi-4-mini's stock arm without ever checking whether that arm emitted.
It had. The second surfaced during re-adjudication: eligibility read a missing
`volunteered_count` as zero, so qwen3.5-0.8b's pre-amendment record came back **eligible**
despite having emitted a quantity. Absence now fails closed, as everywhere else here.

**O-15 is answered early**, without the deferred semifinal experiment. On both qwens the
minimal arm volunteered **3** quantities and the full bake volunteered **0**: same model,
same questions, same thinking guard, and the persona is the only difference. The baked text
is doing safety work, not decorating the prompt.

**Next: steps 2 to 4, which need a human, and the pack is already made.**

    runs/20260820T105919Z_blind/     A.txt  B.txt  C.txt  SCORES.md  SEALED_mapping.b64

The three shipping arms, **candidate-blind**: shuffled, model name withheld, and any
self-identification redacted from the answers, because models introduce themselves. Score
A, B and C on `grounded`, `refusal`, `concise`, `relevance`, fill in `SCORES.md`, put a date
on its COMMITTED line, then `python3 scripts/blind_pack.py --reveal <dir>`. It refuses while
blanks remain.

The reason is the same one behind the timing strip, one level up: the accuracy proxy is
already known and already an anchor, so a scorer who knows which transcript is the accuracy
leader is confirming a number rather than reading a transcript. Then step 3's tie-break to
accuracy would count the same input twice.

**I have not seen this mapping.** An earlier pack was generated and its seal opened while
testing the reveal mechanism; that pack was destroyed and this one made fresh, precisely so
the blind holds if I am asked to help read the transcripts.

Ties break to limit-150 accuracy on the point estimate: qwen3.5-4b 76.16, phi-4-mini 73.67,
qwen3.5-2b 64.17. **Look at those only after the behavioural ordering is committed.**
Runner-up goes into `config.yaml` as the fallback.


## Where the selection actually stands

**The artefact is gone.** The finalist set of one (`qwen3.5-0.8b`), which came from a
composite where five of six candidates had no throughput data and were scored `perf 0.00`,
is superseded by `runs/20260812T205537Z_composite`, built on the complete sweep with
`ranking_complete: true`. The old record stays in the archive marked incomplete, and
`report_figures.py` refuses to publish a finalist set from any composite that says so.

**What exists now is a partition, not a ranking.** Five of six candidates are in the
selection set (everything except `gemma-4-e2b-it`), listed alphabetically because the
throughput term cannot order them: the sweep's own output warned that three candidates
exceeded 25% spread. The record carries `provisional: true` and `ordering_claimed: false`,
and will keep carrying them until a physical run exists. **A selection set of five is not a
result to be pleased with**; it is the accuracy mix at limit 50 failing to discriminate,
which is exactly the case 9f-pre was written for, and the re-run above is the registered
response.

**Accuracy proxy at limit 50** (arc_easy, arc_challenge, mmlu_high_school_biology,
mmlu_nutrition), run `20260812T000207Z_lmeval_sweep`. The in-flight re-run at limit 150 will
supersede these for the five tied candidates:

| candidate | mean |
|---|---|
| qwen3.5-4b | 0.765 |
| phi-4-mini | 0.760 |
| gemma-4-e2b | 0.655 |
| qwen3.5-2b | 0.650 |
| qwen3.5-0.8b | 0.590 |
| llama-3.2-1b | 0.550 |

---

## Blocked on the user

| Item | What is needed | Blocks |
|---|---|---|
| **O-02** | `team_id`, submitter name, email, GitHub handle | `metadata.json` has `TODO_*`; an xfail guards it |
| **O-12** | A **physical machine** near the Standard Laptop spec (4 cores, 8 GB, no GPU), **booked for a full day** if a 3.8 to 4B candidate is in the cluster | Submitted telemetry, ranking **completion** (not verification, SR-12), **and** judge-real latency, in one sitting (section 9g). Critical path |

**O-12 became urgent.** O-13 concluded: six repetitions of one model on this VPS, warm-up
discarded, every one at 0.00% steal, threads fixed at 12, spanned **67.9%**. Not monotonic
so not warm-up, zero steal so not theft. By elimination, neighbour contention on a resource
the kernel does not account to us. **This host cannot rank candidates on throughput at
all.**

Two dated fallbacks now hang off **18 Aug**, and they are separate things:

| | Decides | Fallback |
|---|---|---|
| **9g telemetry fallback** | what number is *submitted* | VPS medians, central-estimate rule, labelled `FALLBACK`, spread documented. Latency never falls back |
| **9f-bis degraded selection** | how the *finalist is chosen* | accuracy + efficiency + behavioural pass; throughput enters as size-class bands only (boundaries fixed at 1 GB and 2 GB), no ordering claimed inside a class |

The degraded path names its own weakness: efficiency is already derived from file size, so
size would drive half the composite weight through two columns that look independent.
Documented rather than adjusted, because adjusting it means inventing a throughput number.

**Budget the sitting as a full day** if a 3.8 to 4B candidate is in the cluster: a
three-arm pass on one 4B is ~5 h at the measured 0.80 tok/s, before the re-bench. Run the
official profiler on **every cluster member first**, because that run is simultaneously the
ranking completion and the submitted telemetry, so an overrunning chat pass costs a finding
rather than the audited number.

**Pre-registered cut if the day runs out:** drop arm 2, never a candidate. Its default is
also registered: ship-full versus ship-minimal follows whichever arm ran clean on the
selected candidate, because the minimal bake is not shippable on no transcript. Persona
isolation then defers to the semifinal window as **O-15**, which costs nothing at Gate 1
since the submitted artefact is fixed at submission and its hash is what Gate 2 re-profiles.

---

## Standing rules that are enforced, not remembered

- **Audit fidelity** (9e-bis): no flag the profiler does not pass may touch a run feeding a
  submitted number. Allowed set is *derived from vendored source*
  (`competition/fidelity_oracle.json`), not hand-listed.
- **Figure rule** (9h): numeric figures enter `REPORT.md` only via
  `scripts/report_figures.py`; measured / retrieved / derived, nothing else.
- **Latency quotability**: only from `--host-class physical`. Consumer-side refusal in
  `run_guards.py`, used by both `composite.py` and `report_figures.py`.
- **Superseded rules**: `competition/superseded.yaml` (12 entries), build fails on
  reappearance.
- **One door onto the archive**: every numeric consumer reads runs through
  `scripts/run_guards.py`. A missing measurement comes back as `Absent`, which raises on
  any numeric use *including truthiness*, so `x or 0.0` cannot resurrect the zero that
  produced the artefact finalist set. A test greps consumers for JSON parsing, archive
  globbing, or a private `RUNS`, and a second test proves that grep can fail.
- **Composite completeness**: a composite recording `ranking_complete: false` publishes no
  finalist set. Same consumer-side pattern as latency.
- **Composite provisionality**: a composite whose bench source does not positively declare
  `host_class: physical` is stamped `provisional: true` and labelled PROVISIONAL wherever
  it surfaces. Complete is not the same as final (section 9f-bis).
- **Partition, not ranking**: a provisional composite emits a `partition` (selection set
  and excluded, both sorted by id, `ordering_claimed: false`) and prints alphabetically,
  so nothing about it reads as an order. `REPORT.md` and `docs/BAKEOFF.md` may not order
  two candidates in prose while no run declares `host_class: physical`; the check is
  candidate-proximity based and exempts claims that state an arithmetic or accuracy basis.
- **Positive controls** (section 12b): no guard ships without a test proving it can fire.
  `GUARD_POSITIVE_CONTROLS` in `tests/test_competition.py` is bidirectional, so a new guard
  with no control and an unregistered control both fail the build. Nine guards covered.
- **Gate 2 comparison is symmetric** and normalises by the *submitted* value:
  underclaiming fails at 1.5x error, overclaiming survives to 2x. Submit the accurate
  central estimate, never a deliberately conservative one (SR-01).

## Next actions, in order

1. Wait for the bench sweep (~12:00-12:30Z); re-run `python3 scripts/composite.py --auto`.
   Then check `python3 scripts/report_figures.py` lists `composite` as AVAILABLE: while it
   is still BLOCKED, the table is incomplete and the finalist set is not real. It will be
   labelled **PROVISIONAL** even once complete, which is correct and stays until the
   physical sitting re-measures perf (section 9f-bis).
2. Apply the pre-registered cluster rule (section 9f-pre) to whatever cluster forms.
   Cluster > 3 fires the limit 150-200 accuracy re-run on tied candidates, official image,
   automatically via `scripts/after_sweep.sh`.
3. Take the tie cluster to the three-arm qualitative pass **on physical hardware only**
   (`scripts/ab_template.py`, `--host-class physical`).
4. Remaining `REPORT.md` `[PENDING]` markers, all genuinely blocked, none fillable here:
   sections 2.1, 2.4 and 2.5 need the finalist set and the qualitative pass; section 4.1
   and the section 4.4 confirmation need O-12 telemetry; section 4.6 needs the three-arm
   pass.
5. From 20 Aug, stop using this list and follow **`SUBMISSION.md`** in order. It absorbs
   the 22 Aug `check_upstream.sh` run as its phase 2 gate.
6. Remaining deliverables: **record the video** to `docs/VIDEO.md`'s beat sheet, which
   needs O-02 for the closing card. CITATIONS.md, the README quickstart, and the CLI
   captures are done.

**Do not add guards.** The layer is frozen: nine guards, nine positive controls. A new one
needs a failure that actually happened, not a failure that could. If you find yourself
writing a tenth, check first whether the thing you are worried about is already refused by
`run_guards`, and whether the effort belongs on the submission artifacts instead.

Gate 1 closes **24 Aug 2026 23:45 PDT**; package target 20 Aug.
