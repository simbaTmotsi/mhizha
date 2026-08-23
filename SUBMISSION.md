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

## Push topology: one machine open at a time

Two machines now edit this repository, and neither can push without Simba. That is the
control, not a limitation to work around: **human pushes are the sync points.**

    VPS      commits through Phase 3
    Simba    pushes
    laptop   clones fresh, commits
    Simba    pushes
    VPS      pulls before touching anything again

**One machine open at a time.** No machine starts work on a tree it has not just pulled,
and no machine assumes its view is current after another has been active. The VPS in
particular cannot pull or push at all: it has no credentials, so its commits sit local
until a human moves them, and a VPS session that begins without a fresh pull is working
from whatever the last human sync left behind.

The laptop **clones fresh** rather than pulling an old working copy. A stale clone is how
the physical-telemetry work would end up merged against a tree that no longer matches the
report it is filling.

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

**The list, so this is a ten-minute pass and not a hunt.** Regenerate it after the figure
slots are filled, because filling them changes what overlaps:

```bash
python3 - <<'EOF'
import re, pathlib
pat = re.compile(r"(\d+(?:\.\d+)?)\s*(tok/s|MB|GB|%|minutes|min\b|seconds|points)")
def nums(path):
    t = re.sub(r"```.*?```", "", pathlib.Path(path).read_text(), flags=re.DOTALL)
    out = {}
    for n, line in enumerate(t.splitlines(), 1):
        for m in pat.finditer(line):
            out.setdefault(m.group(1), []).append(n)
    return out
r, b = nums("REPORT.md"), nums("docs/BAKEOFF.md")
for v in sorted(set(r) & set(b), key=float):
    print(f"{v:>8}  REPORT {r[v][:4]}  BAKEOFF {b[v][:4]}")
EOF
```

Snapshot as of 20 Aug, before the Phase 1.1 fills, ten values overlap: `0.00`, `1.7`,
`5.0`, `8`, `26.5`, `27.8`, `28`, `35`, `40`, `65.5`. The ones worth a second look are
`1.7` and `5.0`, the recomputed answer times, because they were wrong in both documents
until 12 Aug and a stale copy of either would now contradict the other.

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

   **The description is drafted in `docs/YOUTUBE.txt`**, a paste buffer like `DEVPOST.md`:
   plain text, no Markdown, because YouTube renders none. About 2,000 characters against a
   5,000 limit. Its first sentence is written to stand alone, since that is what shows in
   search results and above the fold.

   Three things to do on the upload page, none of which the description can do for itself:

   - **Upload `docs/video/captions.vtt` as a subtitle track.** The mp4 carries a `mov_text`
     track, but YouTube generally will not use an embedded track, and its auto-captions will
     mis-hear *Mhizha*, *Mashonaland* and *AGRITEX* exactly the way the speech model did in
     `--verify`. Upload the file; the timings are measured from the audio.
   - **Check the chapters took.** YouTube builds them from the timestamp list, but only if
     the first is `0:00` and every chapter runs at least ten seconds. Both hold here, with
     the shortest at twelve. If they do not appear, the list is still readable as text.
   - **Set the language to English** so the caption track attaches to the right one.
2. **Fill the Devpost form at `adtc-2026.devpost.com`.** The submission is the repository
   URL, **https://github.com/simbaTmotsi/mhizha**. **Read the actual form on the day rather
   than trusting this paragraph**: neither official repository documents the form fields, so
   what a judge is asked for beyond the repository URL and the video link is not something we
   have retrieved. Treat any field list written here in advance as a guess, which is why
   there is not one.

   **The "About the project" answer is drafted in `docs/DEVPOST.md`.** That file is a paste
   buffer and nothing else: no preamble, no notes, no instructions to a reader. Select all,
   copy, paste. Everything you would otherwise have had to strip out is here instead.

   **It embeds five gallery images by raw URL, and they only resolve once the repository is
   public.** This is the one hard ordering dependency in phase 4: the flip in phase 3 has to
   land before the form is filled, or the story pastes with five broken images. Open the
   preview and look at it rather than trusting this paragraph.

   The URLs point at `master`. Decision **D-09** says history is not rewritten, so that
   reference is stable; if a rewrite ever happens anyway, these break and the tag should be
   used instead.

   - **Preview the LaTeX.** Two display equations, the profiler's own scoring formulas. If
     Devpost does not render them, swap in
     `S_perf = min(TPS / 15.0, 1) x 100` and
     `S_eff = max(0, (7.0 - peak_rss_gb) / 7.0) x 100`, and nothing is lost.
   - **Every figure in it was cross-checked** against `report_figures.py --manifest` on
     23 Aug: 1.82, 3.83, 3.27, 15.0, 67.9 and 1433.78 all resolve to a run record. The
     counts (13 superseded entries, 16 red-team probes, 10 guards, 328 tests, 95/93/81
     blind, the 12-point proxy gap) were each read out of the file that holds them.
     **If you edit a number, re-check it.** The rule that no figure is typed by hand is not
     suspended because the text is going into a web form.
   - ***Built with***, 24 of the 25 allowed. The project first, because a judge skimming
     reads the front of the list:

     ```
     python  llama.cpp  gguf  qwen  rag  sqlite  sqlite-vec  sentence-transformers
     huggingface  numpy  docker  pytest  lm-evaluation-harness  quantization
     offline-first  on-device-ai
     ```

     Then the eight that built the submission video, which are worth having but should not
     come before the stack: `remotion  react  typescript  node.js  ffmpeg  kokoro
     pillow  whisper`.

     **`android` is deliberately absent, and so are `mediapipe` and `mlc-llm`.** The
     product targets a mid-range Android phone and `docs/android-packaging.md` documents
     the path, but **there is no Android code in this repository** — no Kotlin, no Gradle,
     no manifest. A "Built with" tag asserts a thing was used. The story says what the
     target is; a tag would say we shipped to it. Add them when there is an APK.
   - ***Try it out*** is the repository URL.
   - ***Self-reported profiler scores.*** **S_perf `21.79`, S_eff `80.0`.**

     Both use the profiler's own formulas, retrieved from
     `vendor/adtc-profiler/README.md`: `min(TPS / 15.0, 1) * 100` and
     `max(0, (7.0 - peak_rss_gb) / 7.0) * 100`.

     **S_eff is not in question**: peak RSS 1.4 GB, from the same profiler run REPORT.md
     4.1 already cites, and the profiler printed `80.0` itself.

     **S_perf needed a decision, and it is worth understanding before anyone changes it.**
     Two measurements of the selected model exist from the same evening:

     | source | tok/s | S_perf |
     |---|---|---|
     | screened bench, median of 5 kept reps, **what REPORT.md submits** | 3.268 | **21.79** |
     | the profiler's single run, `..._20525079efb1` | 3.590 | 23.93 |

     The profiler printed `23.93` and it is tempting, being both higher and literally "from
     the profiler". **It is one repetition on a host measured at 15.0% spread**, and
     section 9g fixed the rule in advance: the submitted figure is *the median of screened,
     warm, zero-steal repetitions, not the fastest*. Taking the higher sample at
     form-filling time, because it flatters, is the late anchor the blind-scoring
     discipline exists to prevent. Two points of S_perf is not worth telling a second story.

     It is also the sourcing REPORT.md 4.1 already uses: throughput from the screened
     bench, RSS from the profiler run. The form matches the report, and the report matches
     the video and the Devpost page.

     **Neither number is from audit hardware.** Both are our shared host under the section
     9g `FALLBACK`, and the audit box should do better. Gate 2 normalises by the submitted
     value and underclaiming fails at 1.5x error (SR-01), so if asked, say the figure is a
     labelled fallback and point at REPORT.md 4.1.
   - ***Image gallery***, ten images in `docs/gallery/`, 3:2, well under the 5 MB cap.
     `python3 scripts/gallery.py` rebuilds them from material the repository already holds,
     so a stale image is a rebuild away rather than a re-shoot away. **Upload in order; the
     order is the argument.** Captions, if the form offers them:

     | # | file | caption |
     |---|---|---|
     | 1 | `01-mhizha` | Offline agronomy for Zimbabwean smallholders. It cites what it used, and refuses what it cannot source. |
     | 2 | `02-cited-answer` | Every answer names its passages, their publisher, and the date each was refreshed. |
     | 3 | `03-refuses-a-dose` | Asked for a spray rate, it gives none. A dose not written verbatim in a signed-off passage is never emitted. |
     | 4 | `04-abstains` | Below its confidence threshold the model is never called. It says what it does not know and asks one question. |
     | 5 | `05-what-is-profiled` | The competition profiles a bare model file, so our safety posture ships baked into the model's own chat template. |
     | 6 | `06-untraceable-numbers-fail-the-build` | A number that cannot be traced to a run fails our build. Latency is BLOCKED because we never had the hardware to measure it honestly. |
     | 7 | `07-fits-a-4gb-phone` | Every runtime component costed against the headroom an app actually gets on a 4 GB phone. |
     | 8 | `08-chosen-blind` | Transcripts were scored candidate-blind, mapping sealed beforehand. The blind changed the answer. |
     | 9 | `09-what-we-got-wrong` | Thirteen reversed conclusions, each with the evidence that overturned it. The build fails if one comes back. |
     | 10 | `10-no-number-by-hand` | A missing measurement is Absent, never zero. We published the absence and the reason. |

     **Every image is checked for an absolute home path before it is written.** `doctor`
     prints one and the committed capture has it relativised; the generator refuses rather
     than relying on someone remembering the difference.
   - **Two things worth saying if anyone asks in person**: the corpus is placeholder, and
     the dosage refusal is the point.
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
