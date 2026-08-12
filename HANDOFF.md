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

## In flight right now

**The all-candidate throughput sweep completed 12 Aug 20:55Z** and the composite was
re-formed on complete data. See the caveat section below for what it produced.

One background job, started 12 Aug ~20:56Z, the **pre-registered cluster re-run**:

```
python3 scripts/lmeval_mix.py --candidates <the 5 tied> --limit 150 \
    --image adtc-profiler:latest --tag cluster-rerun
  log: /tmp/cluster_rerun.log
```

It fired because the selection set came out at 5, and 9f-pre says a cluster above 3 means
the mix at limit 50 did not discriminate. Tied candidates only, official image only. The
limit-50 sweep of six candidates took about 2.5 hours, so expect this to run several hours;
`arc_easy` and `arc_challenge` dominate. When it finishes:

```
python3 scripts/composite.py --auto      # re-forms the cluster from tighter accuracy bands
```

Then check `python3 scripts/report_figures.py` still lists `composite` as AVAILABLE and
still labels it PROVISIONAL, which it should until a physical run exists.

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
