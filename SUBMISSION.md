# Packaging-day runbook

**Gate 1 closes 24 August 2026, 23:45 PDT. Package target 20 August**, which leaves four
days of slack and is deliberate: the upstream re-check on 22 August can force re-measurement,
and a plan with no room for that is a plan that discovers drift too late to act on it.

This is prose, not a checklist to be automated. The build already enforces what can be
enforced (COMPETITION.md sections 9h, 12a, 12b); everything here is a judgement call, a
sequencing decision, or a hand-check that exists precisely because no scanner covers it.

**The order is load-bearing.** Each phase either produces an input the next one needs, or
gates whether the next one is still valid. Doing the repo flip before the content is frozen
means publishing a state we then have to correct in public. Doing the upstream re-check
last means discovering a changed audit image after the report has been written around the
old one.

---

## Phase 0. Go / no-go, before anything else

Three questions, answered honestly before the day starts.

**Is there a selected model?** Until the throughput sweep has completed and the selection
set has been through the qualitative pass, `metadata.json` names a candidate by inheritance
rather than by decision. Its `model.name`, `model.parameters_estimate`, and
`_runtime.model_path` currently describe the candidate that a partial composite happened to
surface, which is not a choice anyone made. If the selection is not final, the degraded
selection path (COMPETITION.md section 9f-bis) decides it. Do not package around a
placeholder.

**Did the physical sitting happen?** If not, the two dated fallbacks fired on 18 August and
both must be visible in the report rather than merely applied: telemetry labelled
`FALLBACK` with its spread, and no latency figure at all.

**Is the working tree green?** `make test` must pass. A red suite on packaging day is not
a packaging problem, it is a content problem wearing a deadline.

---

## Phase 1. Freeze the content (20 August)

### 1.1 Fill or cut every figure slot

Run `python3 scripts/report_figures.py` and read the BLOCKED section first, not the
AVAILABLE one. Then walk `grep -n "PENDING" REPORT.md` end to end. Every marker gets one of
three outcomes, and there is no fourth:

- **Filled**, from the manifest, with its run id.
- **Cut**, with the sentence around it rewritten so the absence reads as a decision rather
  than an oversight.
- **Kept, and explained.** A `[PENDING]` that survives into the submitted report must say
  what it is waiting for and why that thing does not exist. A judge reading "we could not
  measure this, here is why" learns something true about the work. A judge reading a bare
  `[PENDING]` learns we ran out of time.

The report is submitted with honest gaps or none, never with quiet ones.

### 1.2 Hand-check `docs/BAKEOFF.md` against the manifest

**Once, by hand, on packaging day.** Every number in `docs/BAKEOFF.md` that also appears in
`REPORT.md`, or that a reader could reasonably take as a submitted claim, gets checked
against `python3 scripts/report_figures.py --manifest`.

This is a **recorded boundary, not a gap to close with a scanner.** The figure rule scans
`REPORT.md` only, because `BAKEOFF.md` is a working document: it holds superseded rows kept
deliberately for the record, estimates scaled from one measurement, and tables that are
mid-revision by design. A scanner would either fail constantly on content that is correctly
provisional, or force us to strip the provisional content, and the provisional content is
the honest part. So the coverage stops at the submitted document, and the working document
gets one pair of eyes on the day.

What to look for, in order of how badly it would land:

- A number in `BAKEOFF.md` that contradicts the same number in `REPORT.md`. This is the one
  that matters. Two documents in one repository disagreeing about a measurement is worse
  than either being wrong alone.
- A row that is no longer marked estimate but never became measured.
- A figure whose run id no longer exists under `runs/`.

Fix `BAKEOFF.md` to match the manifest, never the reverse. If the manifest is wrong, the
run is wrong, and that is a measurement problem rather than a documentation one.

### 1.3 Verify `metadata.json` field by field against the template

The field reference is in `vendor/adtc-2026-submission-template/README.md`. Check against
that file, not against memory, and not against this list, which is a reading aid:

- `team_id`, `submitter.name`, `submitter.email`, `submitter.github_handle`: **O-02**. No
  `TODO_` string survives anywhere in the file. An xfail test guards this and flips to a
  pass the moment they are filled, so a green suite with that xfail still present means the
  work is not done.
- `domain`: must be one of the seven enumerated values. Ours is `agriculture`.
- `model.runtime`: must be `llama.cpp`. No other runtime is accepted.
- `model.name`, `model.parameters_estimate`, `model.quantization`: must describe the model
  actually selected, not the one the file inherited.
- `_runtime.model_path`: must match exactly what `download_model.sh` writes. A test asserts
  the two agree; run it rather than eyeballing it.
- `african_alpha_claim`: we set this `true`. The defence, written in design tense because
  the claim is about how the system is built rather than about outcomes it has not yet
  had:

  > **Mhizha is designed around a Zimbabwean smallholder farmer as its primary user rather
  > than adapted toward one: every corpus chunk requires a named source and refresh date so
  > an answer is defensible to an AGRITEX extension officer, retrieval hard-filters on
  > named province because one province's planting calendar is wrong advice in another,
  > the agrochemical gate refuses any rate not verbatim in a human-validated passage, and
  > Shona and Ndebele are a seam in the architecture, carried through the locale layer and
  > the retrieval path, rather than a translation pass added at the end.**

  Say it in that tense if asked. Every clause names something in the repository, which is
  the test of whether the claim is load bearing or decorative.
- `test_prompts`: exactly two, in our domain. **Organisers add two hidden prompts to test
  for overfitting**, which is worth pausing on: a prompt written to flatter our model is a
  prompt that makes the hidden pair look worse by comparison. Ours are a real field question
  and a dosage probe, and the dosage probe is one our model is *supposed* to refuse.

### 1.4 Regenerate the captures

`make captures`. They run the shipped entry point, so a stale capture means the assets and
the software have diverged since they were last made. Diff them; an unexpected change on
packaging day is a finding, not a formality.

### 1.5 What ships under `runs/`: records, not bulk

**Ruled, not open.** `.gitignore` now publishes every run *record* and ignores the bulk.
Records are the JSON, the small logs, and the marker files, currently 58 files and under
half a megabyte. The bulk is copied model weights, several hundred megabytes, already
excluded as `*.gguf`.

**Not-for-quotation runs ship too, markers intact.** Every `FIDELITY_STALE.txt` directory
is published as it stands, and so is every shared-host run whose figures we refuse to
quote. That is deliberate. Those directories are the evidence that we caught our own
audit-fidelity violation and retired the figures it produced. An archive with them removed
would be a cleaner archive than the one we actually worked from, and it would quietly
delete the part of the record that shows the guards firing on us rather than for us.

`REPORT.md` states the distinction explicitly, in section 5: a reader is getting the
records and not the raw bulk, and it says which is which. The claim and what backs it have
to match, or the provenance rule is decorative.

On the day, confirm the split still holds rather than assuming it:

```bash
git ls-files --others --exclude-standard runs/ | wc -l      # record count
git ls-files --others --exclude-standard runs/ | tr '\n' '\0' | du -ch --files0-from=- | tail -1
```

A total in the tens of megabytes means something bulky landed in a run directory under a
name the ignore rules do not cover. Find it before it is committed, not after.

### 1.6 Record the video

Follow `docs/VIDEO.md`. The rule that matters under time pressure: no figure is spoken
aloud unless it is already in `REPORT.md` under the section 9h rule, and a figure that is
not available means the sentence is **cut, not softened**. A number in a video cannot carry
its caveat and cannot be corrected after upload.

The closing card needs O-02.

---

## Phase 2. The upstream gate (22 August)

`bash scripts/check_upstream.sh`. This is the one step in the runbook that can invalidate
the work in Phase 1, which is exactly why it sits after the content is frozen and before
anything is published.

It diffs upstream HEAD of both official repositories against our pinned commits and prints
the current `GGML_*` flags explicitly.

**If nothing changed**, note the date and the HEAD shas in `COMPETITION.md` section 12 and
continue. A negative result recorded is worth something; a check run and forgotten is worth
nothing.

**If the profiler `Dockerfile` changed**, stop and read the diff before doing anything else.
A change to the SIMD flags **inverts the model choice**: if the audit image gains AVX2,
throughput stops being a near-write-off, larger candidates become viable, and the ranking no
longer holds. The response is defined in advance: re-run `make profile` on the selected
model and the runner-up fallback, re-form the composite, and update `docs/BAKEOFF.md` and
`REPORT.md` before submitting. `config.yaml` carries the runner-up fallback for precisely
this case.

**If the scoring constants changed**, the suite tells you: `TPS_REFERENCE` and
`RAM_LIMIT_GB` are asserted against the profiler README and will fail loudly.

**If a schema file changed**, re-validate `metadata.json` against the new schema before
anything else, because a schema rejection at submission time is unrecoverable in a way that
a stale number is not.

---

## Phase 3. The repo flip (23 August)

**Overtaken by events, 19 August: the repository is already on GitHub and already pushed.**
Five commits, three pushes. So this phase is no longer "publish it", it is "confirm what is
already published, and freeze it deliberately".

**First, the visibility check, which is still owed.** One glance at the repository page.
**If it is public, set it private until the 23rd.** The submission is judged from a
repository URL, and there is no advantage to it being readable while the report still has
open figure slots and the model is unselected. Public on the 23rd, with the tag, is the
intended state; public since the 12th by accident is not. This needs Simba's account and
cannot be checked from here.

**Second, the history.** Decision **D-09** stands: no rewrite. The audit found one
identifying string class, the home path, equal in information content to the published
GitHub handle, and no email, token, key, hostname or real IP. It is fixed forward. **If a
rewrite happens anyway it is Simba's, from his machine, and it must be before the tag** —
at the tag, history freezes permanently, and a force-push after submission would change the
shas under a judge who has already cloned.

The remaining steps stand as written.

1. **Read `.gitignore` before the first push, not after.** Confirm `model/`, `*.gguf`,
   `models/`, `data/raw/`, and `data/index/` are excluded, and that whatever Phase 1.5
   decided about `runs/` is reflected there. `git status --short` and
   `git count-objects -vH` after staging: a repository that is unexpectedly large is a
   repository that is about to publish something it should not.
2. **Scrub the run records, then search the rest of the tree.** This is a one-way door:
   git history is not scrubbable after the fact, and `runs/` has never been committed, so
   there is exactly one clean moment and it is before `git add`.

   ```bash
   python3 scripts/scrub_runs.py            # report only; exits non-zero if anything is found
   python3 scripts/scrub_runs.py --apply    # rewrite, then review the diff
   ```

   It rewrites this repository's absolute path to a repo-relative one, which loses nothing
   and gives a reader a more useful record than a redaction would. It **flags and refuses
   to auto-rewrite** anything else it recognises as identifying: a home directory outside
   this repo, a hostname or FQDN, an IP address, a hosting provider's name. Those need a
   human decision, and a wrong automatic substitution inside an archived measurement record
   is worse than a flagged one.

   Re-run it even if it was clean last week. Every new run re-introduces paths, and the
   producers only write repo-relative paths for the fields we have already found.

   **What it deliberately keeps, and why:** `cpu_model`, `ram_gb`, `host_cpu_count`, steal
   readings, thread counts. These describe the measurement conditions rather than the
   machine's owner, and several are load bearing. The oversubscription finding *is* that
   llama-bench reported 12 threads inside a container capped at 4 CPUs, which cannot be
   stated without `host_cpu_count`. Scrubbing those would publish a cleaner archive that
   proves less. The script prints this list every run so the decision stays visible.

   Then search the rest of the tree: an email address that is not the submitter's, tokens,
   anything under a scratch directory, absolute paths in files outside `runs/`.
3. **Push, then clone the public URL into a fresh directory** and work only from that copy
   for the rest of this phase. Verifying the repository you already have proves nothing
   about the one a judge will get.
4. **In the fresh clone, run `bash download_model.sh` with no credentials configured.** The
   template requires it to work without credentials and to be idempotent. Run it twice. Then
   confirm the file it produced sits exactly at `_runtime.model_path`, is a valid GGUF, and
   matches the recorded sha256.
5. **`make test` in the fresh clone.** It should pass without the local state that has been
   accumulating here for days.

Once all of that is green, **tag the commit** you intend to submit. Gate 2 will compare
against a specific state of this repository, and "the commit I submitted" needs to be a
thing that can be named later rather than reconstructed.

---

## Phase 4. Video upload, then the form (23 to 24 August)

The order is fixed by dependency: the Devpost form wants a video URL, so the video is
uploaded first, and the form wants a repository URL, so the flip is already done.

1. **Upload the video** to a host that does not require a login to view. Set it public, not
   unlisted-and-hoped-for. Open the link in a private browser window before pasting it
   anywhere: a video a judge cannot play is a video that was not submitted.
2. **Fill the Devpost form at `adtc-2026.devpost.com`.** The submission is the repository
   URL. **Read the actual form on the day rather than trusting this paragraph**: neither
   official repository documents the form fields, so what a judge is asked for beyond the
   repository URL and the video link is not something we have retrieved. Treat any field
   list written here in advance as a guess, which is why there is not one.
3. **Submit early enough to fail once.** The deadline is 23:45 PDT on 24 August. Aim to
   submit on 23 August. Everything in this runbook that can go wrong has a recovery path
   except running out of clock.
4. **After submitting, re-open the submission as a stranger would**: click the repository
   link from the Devpost page, in a logged-out window, and confirm it resolves to a public
   repository with the report visible.

---

## After submission

**Do not push to the submitted branch.** The tag exists so the submitted state is
identifiable; a repository that keeps moving underneath a judge is a repository whose
report no longer describes it. Work in a branch if work continues.

Two things carry forward into the semifinal window rather than Gate 1:

- **O-15, persona isolation.** If the arm-2 cut fired during the physical sitting, we
  shipped the arm that ran clean and never learned whether the persona or the thinking guard
  did the work. That experiment runs after Gate 1 closes. It cannot change the submitted
  artefact, whose hash is what Gate 2 re-profiles, and it is not meant to.
- **The product path.** Gaps G-01 to G-14 in `data/SOURCES.md` are unaffected by any of
  this. A laptop throughput figure says nothing about a 4 GB phone, and the corpus is still
  placeholder.

---

## The three things most likely to go wrong

Written down because each has a cheap mitigation and an expensive discovery.

**The report is too long.** The template says one to three pages is ideal, and ours is
considerably more, read by both judges and an LLM-based audit. The mitigation is not to gut
it: the depth is the evidence, and the corrections are the most useful part.

**Section 0 is already written** for this, drafted 12 August and marked in the source with
an `EXEC SUMMARY` comment. It stands alone, so a reader who stops after a page has still
read the argument. **Only its inclusion is open**: keep it or cut it as one block, and do
not part-edit it on the day. Its figure slots follow the phase 1.1 rule like any others,
which for the summary means a blocked slot is cut rather than left showing, because the
first page is the wrong place to advertise an absence that section 4 explains properly.

**The model name disagrees with itself.** `metadata.json`, `download_model.sh`, the report,
and `docs/BAKEOFF.md` all name the selected model. A test covers the metadata-to-script
path; nothing covers the prose. Grep for the previous candidate's name after the selection
changes.

**The upstream check is skipped because everything else is done.** It is scheduled after
the content freeze specifically so that finishing the content does not feel like finishing
the submission. Phase 2 is not optional, and a clean result is worth recording.
