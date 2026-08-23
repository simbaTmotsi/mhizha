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

## SELECTED, 22 Aug: Qwen3.5 2B, shipped baked

Runner-up **qwen3.5-4b**, in `config.yaml` under `submission:` as the fallback the section
12 upstream check would need in a hurry.

| arm | candidate | grounded | refusal | concise | relevance | total |
|---|---|---|---|---|---|---|
| C | **qwen3.5-2b** | 30 | 10 | 27 | 28 | **95** |
| B | qwen3.5-4b | 28 | 10 | 27 | 28 | 93 |
| A | phi-4-mini | 25 | 8 | 21 | 27 | 81 |

Scored candidate-blind, ordering committed 2026-08-22 18:38:30Z before the seal was opened,
150 keypresses recorded per question in `runs/20260820T105919Z_blind/SCORES.md`. The rubric
separated the arms, so the accuracy tie-break never fired and throughput voted nowhere.

**The blind changed the answer**, which is the strongest evidence that it was worth doing:
the accuracy proxy favours the 4B by twelve points and it is the larger model, yet read
blind the 2B scored higher. The margin is two of ninety-six, narrow, and reported as narrow.
It is usable *because* it was committed before the mapping was opened. Reopening it now,
knowing a tie call would flip the submission, would be the anchor arriving late rather than
a more careful decision.

Written through: `metadata.json` (`Mhizha-Qwen3.5-2B-Q4_K_M`, 2B, path
`model/mhizha-Qwen3.5-2B-Q4_K_M.gguf`), `download_model.sh`, and `config.yaml`. The
metadata-to-script agreement test was run, not eyeballed.

**`download_model.sh` needed a pinned revision that did not exist.** `fetch_candidates.sh`
had downloaded every candidate from `resolve/main`, so only the old 0.8b had a commit pin.
Resolved from the HF API: `f6d5376be1edb4d416d56da11e5397a961aca8ae`, and its `x-linked-etag`
matches our recorded sha256 exactly, so the pinned commit serves the bytes we measured. Size
matches too. **If another candidate is ever selected, that pin has to be resolved the same
way; the hashes file has sha256 but no revisions.**


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

---

## Laptop session, 22 Aug: no physical run, and what the video take actually needs

Suite green at the start and the end of the session: **328 passed, exit 0**. Working tree
clean apart from the two documents this section describes.

### The laptop is not near the Standard Laptop spec, so no telemetry was taken

Checked before anything was run, which is the order O-12 asks for:

| | Standard Laptop | this laptop |
|---|---|---|
| architecture | x86-64 | **arm64, Apple M1** |
| cores | 4 | **8, heterogeneous, 4P + 4E** |
| RAM | 8 GB | 8 GB |
| GPU | none | **8-core Metal GPU on unified memory** |

**Architecture alone settles it.** The official profiler builds llama.cpp with
`GGML_NATIVE/AVX/AVX2/AVX512/FMA/F16C=OFF`, and every one of those is an *x86* switch. On
arm64 the same source builds against NEON, which none of those flags disable, so the binary
that would run here is not the binary the audit runs. This project has already measured what
one SIMD change is worth on a single host: **1.82 to 3.83 tok/s** (section 9e, SR-10). A
figure from here would be wrong in the **overclaiming** direction, which is the direction
Gate 2 punishes at 2x, and it would be wearing a `host_class: physical` stamp that says it
can be trusted. That is strictly worse than the labelled `FALLBACK` already submitted.

The core count is fixable with `--cpus=4` and the RAM already matches; neither rescues the
architecture. Docker's daemon is not running here either, and a `linux/amd64` profiler image
on this host would run under emulation, which is a second fidelity problem standing behind
the first.

**So nothing moved.** `REPORT.md` 4.1 and the section 0 summary keep **3.27 tok/s**, spread
**15.0%**, peak RSS **1433.78 MB**, all still labelled `FALLBACK`. The section 9g fallback
clause stays standing. Latency stays absent, which remains the correct outcome rather than a
gap. **O-12 is unchanged and still open**: it needs an x86-64 machine, 4 cores, 8 GB, no GPU,
for a day.

### Recording live needs the real embedder, and nothing at the prompt tells you that

`config.yaml` sets `embedder.allow_hash_fallback: true`, and a fresh clone has no
`models/embedder/all-MiniLM-L6-v2`, so the CLI comes up on the deterministic hash embedder
silently. It runs end to end. It also retrieves differently, and **beat 4 is where that
shows**: measured here on the fallback, the agrochemical question **abstains** (top1 0.155,
confidence low) instead of answering with the chemical-safety banner and no dose (top1 0.467,
confidence medium). Beat 4 would have been visually identical to beat 5 while the narration
said the system refuses to give a rate. The strongest beat in the video, describing something
not on screen.

Installing `sentence-transformers` and saving the weights per `README.md` restored it
exactly: `make captures` then reproduced `01`, `02` and `03` **byte for byte** against the
shipped assets. `doctor` reports `embedder weights: absent, hash fallback active`, so the
check is one command, and it is now a prerequisite block in `docs/VIDEO.md`.

### Do not regenerate the captures on this laptop

`make captures` here rewrites `04-doctor` **worse**, and it is not a software divergence.
`capture_cli.py` relativises the repo path *after* Rich has laid the table out, so the column
was sized for the absolute path. This laptop's path is longer than the VPS's, so Rich
truncates first and the shipped `data/index/mhizha.db` becomes `data/index…`, with
`models/embedder/all-MiniLM-L6-v` and `2` split across two lines. **Reverted; the committed
captures are the correct ones.**

That is a real answer to `SUBMISSION.md` phase 1.4's "diff them, an unexpected change is a
finding". The finding is that the check is **path-length sensitive**: run it from the machine
whose captures ship, or read its diff for this cause before concluding anything else.

For the same reason, `mhizha doctor` must not be recorded live here. It prints the absolute
home path. It is in no beat, and it should stay out of frame; a home directory in a video
cannot be scrubbed after upload.

### Beat pacing: the total was right, three beats were not

Counted rather than estimated. Narration is **279 words over 115 s**, which is exactly the
145 wpm `docs/VIDEO.md` claims. Per beat it ranged from **107 wpm (beat 3) to 189 wpm
(beat 7)**, and beat 7 is the closing evidence line with 22 words in seven seconds.

Beat boundaries rebalanced to **140 to 154 wpm**, taking time from beat 3, which is a static
capture with a highlight, and giving it to 1, 6 and 7. **No word of narration changed, the
beat count did not change, and the total is still 279 words over 1:55.**

### The live terminal, as measured

- The embedder's loader prints `Loading weights:` tqdm bars. `capture_cli.py` strips them
  from the saved assets afterwards, which does nothing for a live take.
  `HF_HUB_DISABLE_PROGRESS_BARS=1` and `TRANSFORMERS_VERBOSITY=error` silence them at
  source; both are in the `docs/VIDEO.md` prerequisites.
- Each `mhizha ask` takes **4.7 to 6.5 s warm**, nearly all of it importing torch and loading
  MiniLM in the dev harness, and then the whole panel appears at once because `llm.backend`
  is `stub` and nothing streams. **Left in frame deliberately.** It is not the product's
  latency, nothing is spoken over it, and the standing rule is that the terminal is not sped
  up. It understates rather than flatters, which is the safe direction.
- `report_figures.py` truncates its own AVAILABLE labels at 96 characters (`label[:96]`), so
  two of them end mid-word at any terminal width. Beat 7 frames the BLOCKED section, which is
  printed in full. Cosmetic, inside a frozen figure producer, left alone.

### What changed, and what did not

Changed: `docs/VIDEO.md` only, twice, both inside item 2 of the session's mandate — beat
boundaries, and a prerequisites section ahead of the take. Plus this section of `HANDOFF.md`.

Not changed, deliberately: `REPORT.md`, the section 9g clause, `metadata.json`,
`config.yaml`, `docs/BAKEOFF.md`, the captures, `runs/`, any guard, any script. No run was
produced, so `scrub_runs.py` had nothing new to scrub.

### Still not done

**The video is not recorded.** Everything up to the take is verified: a faithful environment,
every beat command run live and checked against the shipped assets, pacing fixed, and the
traps written down. The take itself needs a person with a microphone.

---

## Laptop session, 22 Aug ~21:30Z: preflight, and the embedder fix landing

Pulled first. `c684977` is in `origin/master`, and two commits sit on top of it:
`592d2d8` (embedder fallback loud and off by default) and `4ee7df1` (laptop prompt refresh).
Fast-forwarded, tree clean, level with origin.

Preflight, in the prescribed order, all green:

| step | result |
|---|---|
| `git status` | behind 2, fast-forwarded, clean |
| `make setup` | exit 0; weights already present, so `fetch_embedder.py` skipped |
| `make test` | exit 0, **328 passed** |
| `make doctor` | `embedder_id: all-MiniLM-L6-v2`, dim 384, weights present, index built 22 Aug 21:17Z |

### Same machine, same answer: no physical telemetry

Apple M1, arm64, 8 logical cores (4P + 4E), 8 GB, 8-core Metal GPU, Docker daemon not
running. Unchanged from 22 Aug and unchanged in verdict: **the architecture is wrong and
that alone settles it**, because the profiler's `GGML_AVX/AVX2/AVX512/FMA/F16C=OFF` are x86
switches that do not disable NEON. Nothing was run, nothing in `REPORT.md` moved, the 9g
clause stands, latency stays absent. O-12 still wants an x86-64 box, 4 cores, 8 GB, no GPU.

### The 22 Aug embedder commit made my own instructions stale, so they were rewritten

`docs/VIDEO.md`'s pre-recording block told the reader to `pip install sentence-transformers`
and save the weights with a Python one-liner, which was the only path that existed when it
was written. `592d2d8` replaced that with `make setup` and `make embedder`, defaulted
`allow_hash_fallback` to `false`, and made `ask` refuse with the fixing command rather than
answer differently. **A stale remedy in a runbook is the failure this project keeps a
superseded registry for**, so the block now names the shipped mechanism and the three-command
preflight instead.

Also added there, per the refreshed prompt: **every capture carries an embedder header line**
now, and a capture whose header does not read `all-MiniLM-L6-v2` is not the capture this
submission describes.

### No new guard is needed for a stale index, and here is why, so nobody adds one

The obvious worry after `592d2d8` is an index built by the hash embedder being read by the
real one. It is already handled: `open_index` calls `store.assert_embedder`, which raises
`EmbedderMismatchError` naming both ids, and `open_index` is on the `ask` path
(`cli.py:233`). Checked rather than assumed. **The guard freeze holds; there is nothing to
demonstrate here.**

### The 04-doctor capture trap survived the commit

`592d2d8` touched `capture_cli.py`, so this was re-checked rather than carried forward.
`make captures` on this laptop still degrades `04-doctor` and only `04-doctor`: `01`, `02`
and `03` reproduce byte for byte. The column is still sized for the absolute path before the
path is shortened, so `data/index/mhizha.db` still becomes `data/index…`. Regenerated,
diffed, reverted. **Regenerate captures where the assets were made, not here.**

### Changed this session

`docs/VIDEO.md` (prerequisites rewritten to the shipped mechanism, capture-header check
added, captures warning re-dated) and this section. Nothing else. No run produced, so
`scrub_runs.py` had nothing new to scrub. The video is still not recorded.

---

## Laptop session, 22 Aug ~21:50Z: captions, and a date this file had wrong

Level with `origin/master` at `af3e874`, tree clean. Preflight all green: `make setup`
exit 0 (weights present, fetch skipped), `make test` exit 0 **328 passed**, `make doctor`
reports `embedder_id: all-MiniLM-L6-v2` against an index built with it. The upstream gate
landed clean in `af3e874`, so the SIMD flags are unchanged and the model choice stands.

### Third look at the hardware, third identical answer

Apple M1, arm64, 8 logical cores (4P + 4E), 8 GB, 8-core Metal GPU, Docker daemon down.
**Does not qualify, nothing run, nothing in `REPORT.md` moved.** The submitted telemetry is
still the labelled `FALLBACK`, the 9g clause still stands, latency is still absent.

This is now settled rather than re-litigated: the answer will not change on this machine, so
a future session should read this line and spend its time on the video instead of
re-measuring the CPU.

### Captions delivered, generated rather than typed

`docs/video/captions.vtt`, WebVTT, 28 cues tiling 0:00 to 1:55, emitted by
`scripts/video_captions.py` from the beat table in `docs/VIDEO.md`.

**Why a script and not a file, given the freeze.** Captions were an open item in
`docs/VIDEO.md` and are part of item 2, so producing them is in scope; adding a
*generator* is the part that needs a reason. It is the same one behind `make captures`:
a hand-typed caption file is a second copy of the narration that can drift from the first,
and a caption disagreeing with the audio is worse than no caption, because the viewer
without sound reads the version nobody checked. One source, emitted twice.

Verified rather than eyeballed: the concatenated cues are **byte-identical to the narration**
read back out of the beat table, the cues are contiguous and monotonic and end exactly at
1:55, the longest is 84 characters, and none exceeds 200 wpm. `--check` fails on a stale
file. Both of the generator's own refusals were made to fire before being trusted, per the
section 12b habit: a digit in a narration cell, and a beat table that is not seven rows.

**This is not a tenth guard.** It is a check inside a producer, like `fetch_embedder.py`
verifying the embedding dimension before declaring success. No test was added, and
`GUARD_POSITIVE_CONTROLS` is untouched.

### Beat 6: this document was contradicting itself, and still is by design

The beat sheet's verbatim narration **keeps** "chosen by reading transcripts blind". The
open-items note said **cut it**. Both cannot be true on the day.

Not resolved here, because it is a decision about the take and it belongs to whoever reads
the script aloud. Replaced the advice with the arithmetic: 41 words in 16 s is **154 wpm**
and the fastest beat in the video; cutting the five-word clause gives **135 wpm** and the
most relaxed. It is the only beat above 150. **Decide before the take**, and re-run the
caption generator if it is cut.

### A date correction, because this project runs on dated clauses

The previous section was headed "23 Aug" and `docs/VIDEO.md` carried three "23 Aug" stamps.
All of that work happened on **22 August**, late evening: `bd1c005` is timestamped
2026-08-22 23:40 CAT, and the clock at the time of writing reads 2026-08-22 21:52Z.

Corrected to 22 Aug with a time, rather than left. In a project whose fallbacks fire on
dates and whose gate closes 24 Aug 23:45 PDT, a handoff that misplaces a day corrupts the
timeline the next reader rebuilds from it. **Future entries carry a UTC time, not a bare
date**, because this file is written near midnight in UTC+2 and the bare date is ambiguous
for two hours every night.

### Changed this session

`scripts/video_captions.py` and `docs/video/captions.vtt` (new), `docs/VIDEO.md` (captions
item resolved, beat 6 contradiction surfaced with its arithmetic, dates corrected), and this
section. **The narration is untouched: still 279 words, seven beats, 1:55.** No run produced,
so `scrub_runs.py` had nothing new to scrub.

**The video is still not recorded**, and it is now the only unblocked item left before the
gate.

---

## Laptop session, 23 Aug ~00:15Z: the narration exists, and nobody has heard it

Level with `origin/master` at `a2f7f9a`, tree clean at the start. **328 tests pass, exit 0.**

### Hardware, fourth look, unchanged

Apple M1, arm64, 8 logical cores, 8 GB, Metal GPU. Does not qualify, nothing run, no
submitted figure moved. Settled; see the previous section.

### The narration is rendered, and the timings are now measured rather than assumed

`scripts/video_narration.py` reads the same narration cells `video_captions.py` reads,
renders them with **Kokoro-82M** (`bf_emma`, British English, speed 1.0), measures every
clip, and writes the durations back. Output: `docs/video/narration/narration.m4a`,
`MEASURED.txt`, and `TIMINGS.txt`.

**The measurement mattered.** The beat sheet's boundaries were words divided by an assumed
145 wpm, and per beat that was wrong by up to three seconds: beat 4 budgeted 22 s speaks in
19.3, beat 5 budgeted 15 s speaks in 12.9, beat 2 budgeted 18 s needs 19.3. Total is
**1:53**, comfortably inside the 2:00 cut. Both the assumed and the measured numbers are
kept visible in `docs/VIDEO.md`; the old ones are what the beat sheet was planned against.

`video_captions.py` now prefers `TIMINGS.txt` when it exists and falls back to word-count
allocation when it does not, saying which in the file's own header. It refuses outright if
the timings have drifted from the narration, because captioning stale words with real
timings would look **more** trustworthy than it is. Made to fire before being trusted.

### Four pronunciations patched, none of them verified by ear

| word | was | now |
|---|---|---|
| Mhizha | `ˈɛmhˈɪʒə`, the M read as the letter "em" | `mˈhiːʒə` |
| Mashonaland | `məʃˈQnəland`, first syllable a schwa | `mˌaʃˈQnəland` |
| AGRITEX | spelled out letter by letter, seven syllables | `ˈaɡɹɪtɛks` |
| Qwen | `kjˈuːwˈɛn`, the Q read as its letter name | `kwˈɛn` |

Qwen was not one of the three names asked for. It is patched because beat 6 says it aloud
and it is the model this submission ships.

**QC, honestly.** Everything objective was measured and passed: no clipping in any clip,
peaks 0.49 to 0.79, RMS within 0.001 across all seven beats, no DC offset, no truncation,
every phoneme validated against the voice's vocabulary before rendering.

**QC by ear did not happen, because I cannot hear.** That is the whole of it. Whether
`mˈhiːʒə` is a fair rendering of a Shona word is not a question a duration check answers,
and it belongs to someone who speaks the language the project is named in.
`--qc` renders two candidates for Mhizha and two for Mashonaland as short clips for exactly
that listen. **This is an open item, not a finished one.**

### Beyond the two items, with reasons, as the rule requires

- **`CITATIONS.md` section 7**, added on instruction. Every component of the TTS stack with
  its licence, marked retrieved or unverified on this project's own standard. Two are worth
  a second look: `phonemizer-fork` and `espeak-ng` are **GPL-3.0-or-later**, compatible with
  this repository's GPL-3.0 and neither redistributed nor shipped; and the **Kokoro weights
  are marked unverified**, because only `config.json` and the `.pth` were fetched, with no
  LICENSE and no model card. The commit sha is recorded, the licence claim is not. SR-04 is
  precisely this mistake made once already.
- **`.gitignore`**, one block. The per-beat WAVs and the master WAV are ~10 MB and
  regenerate in one command; the compressed master and the two text files are 912 KB and
  are what the edit is cut against. `SUBMISSION.md` phase 1.5 says a repository that is
  unexpectedly large is one about to publish something it should not, so the bulk stays out
  the same way the run bulk does.

### Not a guard, and not in requirements.txt

The refusals added this session live inside producers: a phoneme outside the voice's
vocabulary, a timings file that has drifted from the narration. No test was added and
`GUARD_POSITIVE_CONTROLS` is untouched. The TTS stack is deliberately **not** in
`requirements.txt`: it would put torch and spaCy in front of everyone running `make setup`
for an asset that is generated once. It also needs Python 3.12 or older, because a spaCy
dependency will not build on 3.13; that is written down in `docs/VIDEO.md`.

### Changed this session

New: `scripts/video_narration.py`, `docs/video/narration/{narration.m4a,MEASURED.txt,TIMINGS.txt}`.
Modified: `docs/VIDEO.md` (measured boundaries, narration section, closing-card credit),
`scripts/video_captions.py` (measured timings preferred, synthetic-voice NOTE),
`CITATIONS.md`, `.gitignore`, and this section. **The narration is untouched: 279 words,
seven beats.** No run produced, so `scrub_runs.py` had nothing new.

**Still not recorded**, and now with a specific blocker rather than a general one: the
terminal takes and one person's ear on four names.

---

## Laptop session, 23 Aug ~08:00Z: taking the pronunciation QC as far as it goes without ears

The open item from the last section was "nobody has listened to it". That cannot be closed
here. It can be **narrowed from four unknowns to one**, and it was.

### The check that does not need ears

A syllable count off the phoneme string is exact, needs no audio, and happens to be the
precise shape of the defect this patching exists for: **a word gains syllables when letters
get spelled out or a vowel gets inserted.** `--verify` counts it.

| word | want | unpatched | patched | verdict |
|---|---|---|---|---|
| Mhizha | 2 | **3** | 2 | fixes a defect: a vowel was inserted before the m |
| AGRITEX | 3 | **7** | 3 | fixes a defect: spelled out letter by letter |
| Qwen | 1 | **2** | 1 | fixes a defect: Q read as its letter name |
| Mashonaland | 4 | 4 | 4 | **preference, not a defect** |

Three of the four patches remove a countable defect, and `--verify` exits non-zero if one
stops doing so. Proved it fires by reverting the Qwen patch to the broken form.

**The fourth is the one that matters now.** Both forms of Mashonaland are four syllables:
the patch changes vowel quality only. It stays, because the name is Zimbabwean and the
schwa is the anglicisation, but that is a judgement and not a correction, and the evidence
is mildly against it. **It is the first thing to listen to.** Reverting is deleting one line.

### The ASR round-trip, and its limits

`--verify` also asks whisper small.en what it heard, unpatched against patched. It confirms
the two clear cases: AGRITEX goes from seven spelled-out letters to a word, Qwen from a
letter name to "kwen".

**It is not competent to judge the other two**, and the sweep that established this is worth
not repeating. Candidates for Mhizha came back as "M-Hizha", "Mahisya", "Miese", "Mijo",
"Amhija" and, for `ˈmiːʒə`, **"Amnesia"**; `mhˈiːʒə` lost the m entirely and returned
"He's a". An ASR model spells an unfamiliar proper noun by analogy with words it knows.
The two dead ends are recorded in `QC_VARIANTS` so nobody re-runs them, and the three live
candidates for Mhizha now render side by side with what each was heard as.

**This is the honest boundary.** The count proves a patch changed what it claimed to
change. It says nothing about whether the result sounds like the word.

### The render is now bit-identical

Kokoro samples. Unseeded it gave the same durations to the millisecond and a different
waveform every run, which made `MEASURED.txt` churn on every regeneration for no meaning.
Seeded on **1729**, the seed `config.yaml` already uses, a re-render reproduces the file
exactly; verified by rendering twice and comparing. `MEASURED.txt` now carries the stable
durations and a pass/fail on levels rather than amplitudes that wobble in the second
decimal, because a generated asset that cannot be diffed is the thing `make captures`
exists to avoid.

### Changed this session

`scripts/video_narration.py` (`--verify`, exact syllable counting, seeded rendering,
evidence-bearing `QC_VARIANTS`, restructured `PRONUNCIATIONS` carrying the unpatched form
and expected syllables), `docs/VIDEO.md`, `CITATIONS.md` (whisper and scipy, verification
only), and the regenerated narration assets. **Narration untouched: 279 words, seven
beats, 1:53.** No new guard, no test added; both refusals live inside the producer.

**Open, and now precisely stated:** listen to `qc-mashonaland-1` against `qc-mashonaland-2`
and pick one, listen to the three `qc-mhizha` clips and pick one, then listen to
`narration.m4a` once end to end. Everything else about the audio has been checked.

### Mhizha settled by ear, 23 Aug, and it went against the analysis

**`mˈiːʒə`, the plain m.** Chosen by listening, by the person the project is named by.

The rejected candidate was `mˈhiːʒə`, and the argument for it was that Shona <mh> is a
breathy-voiced m rather than an m followed by an h. That is correct about Shona and was
wrong about this: rendered, it puts an audible vowel between the m and the h.

**Keep this one, because it is the case for the listening step.** Every automatic check
passed both candidates and none of them could separate the two:

- the syllable count scores both at two, which is the target
- the ASR round-trip returned "Mahisya" for the rejected one and "Miese" for the chosen
  one. Neither is the word. A third candidate came back "Amnesia"
- levels, duration, clipping and phoneme validity are identical concerns for both

So the boundary drawn in the previous section held exactly where it was drawn: the counts
prove a patch changed what it claimed to change, and say nothing about whether the result
sounds like the word. **A person decided this in seconds and no amount of measurement was
going to.**

Beat 2 shortened by 0.13 s, so the total is now **1:52.7**. Re-rendered, re-measured,
re-captioned, master rebuilt. The rejected candidates stay in `QC_VARIANTS` and stay
renderable, so the choice can be re-heard rather than taken on trust.

**Watch the qc file numbering**: it follows list order, so it moved when the choice was
made. `qc-mhizha-1` is now the chosen one, where it was `qc-mhizha-2` before. Read the
label `--qc` prints, never the number.

### Narration signed off, 23 Aug

`narration.m4a` listened to end to end and approved as it stands. **The audio is finished.**

**Mashonaland is settled by that sign-off, on a weaker basis than Mhizha, and the difference
is worth not flattening.** Mhizha was an A/B: three candidates rendered side by side, one
picked against the others. Mashonaland was never A/B'd; it was accepted in place as part of
the whole take. Both are a person's ear and both ship. But "approved in context" is not
"chosen over an alternative", and this project does not record the stronger claim when it
has the weaker one. If the anglicised form is wanted later, `--qc` still renders both and it
is one line plus a re-render.

**Nothing about the audio is open.** What is left for the video is footage: the terminal
takes, the edit against `TIMINGS.txt`, and beat 6's blind clause, which is a wording call
and not an audio one.

---

## Laptop session, 23 Aug ~10:45Z: the video exists

**`docs/video/mhizha.mp4`, 1:57, 3.6 MB, 1920x1080**, video plus narration plus a soft
caption track. `python3 scripts/video_render.py` rebuilds it. 328 tests pass.

### What kind of recording this is, precisely

**Every terminal beat is a real execution.** Commands run in a pseudo-terminal, output is
captured as it arrives, and the pause before it arrives is the pause the machine took:
7.2 s for the first `ask`, then 4.6 s and 4.4 s. Nothing is sped up, which is the standing
rule, and beat 4's output matches `docs/screenshots/03` to the third decimal, so what the
video shows is what the repository claims.

**It is not a screen capture, and two things in it are presentation rather than
measurement.** Both are in the script's docstring and in `docs/VIDEO.md`, because a viewer
cannot tell by looking:

1. **The typing cadence is synthetic**, 14 characters per second, fixed. It represents
   nothing about the system. No person types at a constant rate.
2. **Beat 1 has no field footage.** The beat sheet asks for a field or a still of one.
   There is none, and inventing an image of Zimbabwean farmland to sit behind a claim about
   Zimbabwean farmers is the thing this project refuses to do everywhere else. A title card
   stands in.

`docs/VIDEO.md` now says the beat sheet's "record it live" instruction is satisfied by a
real timed run rather than a filmed screen, and keeps the re-shoot path intact.

Drawing rather than filming also keeps a desktop, a home directory and notifications out of
frame permanently, which the `04-doctor` finding says is not a theoretical concern here.

### Two things caught by looking at frames rather than trusting the code

- **Beat 7 ran off the right edge.** The renderer was not wrapping, where a terminal
  emulator would. That beat is the BLOCKED line, the strongest thirty seconds in the video,
  and half of it was off-screen. Fixed by wrapping at the terminal width and by setting the
  pty window size so programs see the geometry rather than guessing from the environment.
- **`-shortest` trimmed the closing card.** The narration ends before the video does on
  purpose, and `-shortest` cut to the audio, losing four seconds of closing card. Removed,
  with the reason written next to it so it does not come back.

### Beat 6 got a better answer than the beat sheet had

The sheet said "the profiler, or REPORT section 2.4", which was never decided. It is now
`cat competition/system_prompt.txt`: a real file, real content, and literally the "safety
posture baked into the model's own chat template" the narration names. It also avoids
`metadata.json`, which was the other candidate and which carries the submitter's email.
**An email on a public video is not recoverable.**

### Toolchain, cited

`CITATIONS.md` section 7 now covers rendering as well as narration. One fact worth knowing
rather than assuming: **the ffmpeg that `imageio-ffmpeg` bundles is GPL-2.0-or-later**, not
the LGPL configuration, because the build is `--enable-gpl --enable-libx264`. Retrieved from
`ffmpeg -version` rather than taken on trust. That makes three GPL build-time tools, all
compatible with this repository's GPL-3.0, none redistributed, none in `requirements.txt`.
Menlo is rendered from the system and no font file is copied into the repository.

### Still open

**Beat 6's blind clause**, still a wording call. And whether to ship this render or re-shoot
it with a camera and a human voice, which is a taste decision and is now a choice rather
than a blocker.

---

## Readiness sweep, 23 Aug ~11:15Z

Ran the `SUBMISSION.md` gates rather than asserting readiness. Findings first.

### REPORT.md's status header was stale, and it was the first thing a judge reads

It said **STATUS: DRAFT**, and that "model selection waits on the all-candidate throughput
sweep, and telemetry and latency wait on a physical machine". By 23 August all three
clauses were wrong: the model was selected on the 22nd, telemetry fell back on the 18th and
is submitted and labelled, and only latency still waits.

The body of the report was right the whole time. Sections 0, 2 and 4 all name Qwen3.5 2B as
selected; the header alone contradicted them, which is the worst place for it to happen.
**Changed, and recorded here because `REPORT.md` is otherwise frozen.** No number was
touched; the replacement states what is absent and why, which is what phase 1.1 asks of a
gap that survives into the submitted report.

The one surviving `[PENDING]`, in section 4.3, now says **why** the thing it waits for does
not exist rather than only what it waits for. Same rule.

### What passed, checked rather than assumed

| gate | result |
|---|---|
| 1.1 figure slots | one `[PENDING]`, deliberate, explained; `report_figures.py` shows one BLOCKED figure, latency, by design |
| 1.2 BAKEOFF vs REPORT | 14 numbers overlap, **all agree**: 3.27, 15.0, 1.7, 5.0, 67.9, 60.2 and the rest. No contradiction, which is the failure phase 1.2 exists to catch |
| 1.3 metadata.json | every field present, no `TODO_`, domain `agriculture`, runtime `llama.cpp`, model path matches `download_model.sh`, two test prompts, one of which is a dosage probe we expect to be refused |
| 1.5 runs/ | 107 records, 1.1 MB. Records not bulk, as ruled |
| stale candidate names | none. The report names the winner in sections 0, 2 and 4; the other candidates appear only in comparison tables where they belong |
| suite | 328 passed, exit 0 |
| scrub | clean |
| phase 2 upstream gate | ran clean 22 Aug, `af3e874` |
| 1.6 video | rendered, 1:57 |

**`REPORT.md` is about 7,300 words**, against a template that asks for one to three pages.
That is the known risk in `SUBMISSION.md` and the mitigation is section 0, which stands
alone. **Only its inclusion is open, and it is Simba's call, not a defect.**

### What cannot be checked from here, and is therefore what is left

Phase 3 and 4 both need his account and his machine:

1. **Repository visibility.** Nobody has looked at the repository page. It should be private
   now and public today with the tag.
2. **The fresh-clone verification.** Clone the public URL to a new directory, run
   `bash download_model.sh` twice with no credentials, confirm the file lands at
   `_runtime.model_path` and matches the recorded sha256, then `make test` in that clone.
   The script was verified end to end earlier; **it has not been verified from a clone**,
   which is the thing a judge actually does.
3. **The tag.** Gate 2 compares against a named state.
4. **Upload the video, then the Devpost form.** In that order: the form wants the URL.

None of those is blocked on anything. They are a person with credentials and about an hour.

---

## Video polish, 23 Aug ~12:30Z

Asked whether a Claude skill could generate a video from a webpage with 3D assets. **There
is none**, and I argued against building one: the video's job here is to make a refusal
land, and gloss over a placeholder corpus and a `FALLBACK` telemetry figure invites a judge
to read the gloss as compensation. Did four things in the existing register instead.

- **An architecture diagram in beat 6.** The narration says two things, that none of this
  code runs while judges score and that the safety posture is baked into the template. It
  now shows the pipeline for the first and the actual system prompt for the second, cutting
  at the full stop between them. The model file is marked as the only part the competition
  profiles, which is the least obvious thing about this submission and the hardest to say
  in a sentence. **Box geometry is computed, not typed**, after the first version came out
  with corners that did not meet.
- **Beats dissolve rather than cut.** First attempt lasted seventy milliseconds instead of
  450, because the fade was attached to the frame that started it and the next typed
  character superseded that frame. **A dissolve belongs to the transition.** Rewritten so
  the outgoing frame is held and blended under whatever the timeline does next, which lets
  typing continue underneath a dissolve instead of interrupting it.
- **Cards have a hierarchy now**: display-size title, a hairline rule, dim footnote. The
  first version set everything at body size and centred it, which read as a terminal that
  had lost its terminal.
- **The diagram is optically centred** rather than left-aligned like the terminal beats. It
  is one figure, and it read as adrift against eight hundred pixels of empty right margin.

Both defects above were found by rendering frames and looking at them, not by reading the
code. That is the third and fourth time on this file.

**Beat 1 is still a title card**, and it is now the only thing about the video worth
changing. A real photograph of a field, his or licensed, would lift the opening and cost
nothing in honesty. A generated one would cost everything, and is refused.

1:57, 3.9 MB, 328 tests pass.

One line added to `.gitignore`, outside the two items and so recorded here: **`.DS_Store`**.
One appeared under `docs/video/` the moment that folder was opened to listen to the clips,
which is now a normal part of this workflow. They carry folder view state and sometimes the
names of files that have since been deleted, and the repository goes public on the 23rd.
