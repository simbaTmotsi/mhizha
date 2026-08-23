# Two-minute video: script skeleton

**Status: skeleton, not yet recorded.** Requirement C-07, treated as mandatory (the
2-minute video is not specified in either official repository, so we assume it is required
rather than discover otherwise on 24 August).

Target length **1:55**, leaving margin against a hard 2:00 cut. Everything below is timed
to be spoken at an unhurried pace, roughly 145 words per minute.

---

## The rule this script follows

**No figure is spoken aloud unless it is already in `REPORT.md` under the section 9h rule.**
A number in a video cannot carry its caveat, cannot be corrected once uploaded, and is the
easiest place in the whole submission for a stale measurement to survive. Slots marked
`[FIGURE: ...]` stay as on-screen text pulled from the report at recording time, or are cut.
If a figure is not available by the recording date, **the sentence is cut, not softened**.

Two further rules, from the same discipline the code enforces:

- **No claim about the corpus.** The corpus is placeholder and the video says so plainly.
  A demo that implies real agronomic content would be the exact failure the whole system
  exists to prevent.
- **No latency claim** unless a physical run exists by recording time. Saying "it answers
  in about N seconds" over a screen recording made on a shared VPS would be a measured-
  sounding claim about a machine nobody will use.

---

## Beat sheet, with the narration written

**Status: ready to record as of 22 Aug.** Both blockers cleared: the model is selected and
the submitter details are filled. Narration is 279 words, which is 1:55 at an unhurried
145 words per minute. **No figure is spoken anywhere in it**, deliberately: a number in a
video cannot carry its caveat and cannot be corrected after upload, so the report keeps the
numbers and the video keeps the argument.

**Beat boundaries rebalanced 22 Aug, narration untouched.** Counted rather than estimated,
the beats ranged from 107 words per minute to 189, even though the total was exactly the
145 the paragraph above claims. Beat 7 had 22 words in seven seconds and it is the closing
evidence line. Time moved from beat 3, a static capture with a highlight, into beats 1, 6
and 7. Every beat came out between 140 and 154 wpm, **no word of narration changed**.

**Superseded 23 Aug: the boundaries below are measured, not calculated.** The rebalance
above was still arithmetic, words divided by an assumed rate, and the narration has now
been rendered so there is a real duration to read instead. It runs **1:53**, and the
per-beat error in the arithmetic was up to three seconds: beat 4 was budgeted 22 s and
speaks in 19.3, beat 5 was budgeted 15 s and speaks in 12.9, beat 2 was budgeted 18 s and
needs 19.3. Both figures are kept visible rather than one quietly replacing the other,
because the assumed numbers are what the beat sheet was planned against.

The table is rounded to the second, which is the resolution a person reads a beat sheet at.
The windows the captions are actually built from are in
`docs/video/narration/TIMINGS.txt`, to the millisecond. Adjacent beats can therefore show
the same second on this table: they are about a third of a second apart, and the rounding
cannot say so.

| # | Time | On screen | Spoken, verbatim |
|---|---|---|---|
| 1 | 0:00-0:16 | A field, or a still of one. Then the terminal. | "A farmer in Mashonaland is deciding what to plant this week. The nearest extension officer is a bus ride away, and there is no signal in the field. An assistant that needs a network is not there at the moment the decision gets made." |
| 2 | 0:17-0:36 | `mhizha ask` running, answer appearing | "Mhizha runs entirely offline, on a mid-range Android phone. It answers practical agronomy questions from a curated corpus, cites what it used, and says so when it cannot help. The pipeline is real. The agronomy is not sourced yet, and we say that plainly." |
| 3 | 0:36-0:55 | Capture 01, sources table highlighted | "Every claim carries a passage, and every passage names its source, its publisher and the date it was refreshed. Those placeholder banners are real. This corpus holds no agronomic content, and the system tells the farmer that instead of sounding authoritative." |
| 4 | 0:55-1:14 | Capture 03. Type the question in full. | "Ask it how much to spray, and it refuses. A dose that is not written, word for word, in a passage a human has signed off is never emitted. Not as an estimate, not as a typical figure. A wrong spray rate destroys a season, or harms the person holding the sprayer." |
| 5 | 1:15-1:28 | Capture 02, the abstention panel | "Below its confidence threshold, the model is not called at all. It says what it does not know, asks the one question that would unblock it, and sends the farmer to their local AGRITEX officer." |
| 6 | 1:28-1:45 | The profiler, or REPORT section 2.4 | "The competition profiles a bare model file, so none of this code runs while judges are scoring. We ship Qwen three point five, two billion, chosen by reading transcripts blind, with our safety posture baked into the model's own chat template." |
| 7 | 1:45-1:53 | `python3 scripts/report_figures.py`, BLOCKED lines visible | "A number that cannot be traced to a run fails our build. Where we could not measure something, the report says so." |

**Closing card:** Mhizha. Simbarashe Timothy Motsi. team_id `mhizha`. github.com/simbaTmotsi.
Below that, smaller: **"Narration: Kokoro-82M, a synthetic voice."** A viewer who assumes a
person read this is owed the correction, it costs one line, and the same credit is in the
caption file's header and in `CITATIONS.md` section 7.

**On beat 6, say the model name aloud as words**, not as a filename. "Qwen three point five, two billion" is what a listener can follow; `qwen3.5-2b-q4_k_m` is not.

## Before you record: the machine has to be able to show beat 4

**Checked on the laptop, 22 Aug, twice. Without this the strongest beat shows the wrong
screen.**

Beat 4 depends entirely on retrieval. On the deterministic hash embedder the agrochemical
question **abstains** (top1 0.155) instead of answering with the chemical-safety banner and
no dose (top1 0.467), so beat 4 becomes visually identical to beat 5 while the narration
says the system refuses to give a rate.

**This is now guarded rather than silent**, as of 22 Aug: `allow_hash_fallback` defaults to
`false`, `make setup` fetches the weights, and `ask` refuses with the command that fixes it
rather than answering differently. `open_index` also raises `EmbedderMismatchError` if the
index on disk was built by a different embedder than the configured one, so a stale index
from before 22 Aug cannot answer quietly either. None of that removes the check; it just
means the machine tells you instead of you having to know.

Run the preflight and read three things:

```bash
make setup      # deps + embedder weights. Needs network, once.
make test       # 328 passed, and check the exit code
make doctor     # embedder_id must read all-MiniLM-L6-v2, never hash-fallback:384
```

If `doctor` reports a hash fallback, or an `embedder_id` on the **index** row that is not
`all-MiniLM-L6-v2`, run `make build` before trusting a single answer on screen.

Verified 22 Aug ~21:30Z on a tree level with `origin/master`: with the weights present, `make
captures` reproduces `01`, `02` and `03` byte for byte against the shipped assets. That is
the check that the machine in front of you shows what the submission claims.

**Every capture now carries its embedder in a header line.** If you re-record a capture,
read that header before you use the footage:

```
# embedder: all-MiniLM-L6-v2   (retrieval depends on this; a different embedder gives different passages)
```

A capture whose header does not say `all-MiniLM-L6-v2` is not the capture this submission
describes, whatever else looks right about it.

**Silence the loader before the take.** The embedder writes `Loading weights:` progress bars
to the terminal. `capture_cli.py` strips them out of the saved assets afterwards, which does
nothing for a live recording. Export these in the recording shell:

```bash
export HF_HUB_DISABLE_PROGRESS_BARS=1 TRANSFORMERS_VERBOSITY=error
```

**Expect a pause after Enter.** Each `ask` takes four to seven seconds warm, nearly all of it
importing torch and loading MiniLM in the dev harness, and then the whole panel appears at
once because `llm.backend` is `stub` and nothing streams. Leave it in frame and do not cut
it. It is not the product's latency, nothing is spoken over it, and the standing rule below
is that the terminal is not sped up.

**Do not record `mhizha doctor`.** It prints the absolute path of the config, the index and
the embedder, which on a personal machine is a home directory. It is in no beat. A home
directory in a video cannot be scrubbed after upload.

**Do not run `make captures` to "refresh" anything first.** On a machine whose repo path is
longer than the one the assets were made on, it degrades `04-doctor`: `capture_cli.py`
relativises the path *after* Rich has sized the column, so Rich truncates the absolute path
first and `data/index/mhizha.db` ships as `data/index…`, and the embedder path breaks across
two lines. The committed captures are the correct ones.

Re-checked 22 Aug ~21:30Z against the embedder commit, which touched `capture_cli.py`: the
column is still sized before the path is shortened, so this is unchanged. `01`, `02` and
`03` still reproduce byte for byte here; only `04-doctor` degrades, and only on this
machine's longer path. If a capture genuinely needs regenerating, do it where the assets
were made.

## What to record, and in what order

Record in this order so a re-take of the hardest beat does not invalidate the others.

1. **Terminal captures first.** `python3 scripts/capture_cli.py --list` names the four
   commands. Record them live rather than showing the saved SVGs, so the timing is real.
   Beat 4 needs the agrochemical question typed in full, because seeing the question is
   what makes the refusal land. Budget for it: typed at a natural pace it is most of the
   beat, which is why beat 4 is the longest one.
2. **`python3 scripts/report_figures.py`** for beat 7. Its BLOCKED section is the strongest
   thirty seconds of evidence in the project and needs no narration beyond one line. Frame
   the BLOCKED block, not the whole output: the script truncates its own AVAILABLE labels
   at 96 characters, so two of them end mid-word at any terminal width. BLOCKED prints in
   full.
3. **The voiceover already exists**, which inverts the old instruction here. It used to
   say record the voice last, against the cut, so the pacing followed the footage. The
   narration is now rendered and measured, so the footage is cut to it: every beat has a
   known duration and `docs/video/narration/TIMINGS.txt` gives the cut points to the
   millisecond. Lay the audio down first and fit the terminal takes into its windows.

   If you would rather read it yourself, do: a human voice is better than a synthetic one
   and the script was written to be spoken. Then re-time the beats against your own
   recording rather than keeping these, and re-run `scripts/video_captions.py`.

## The narration, and what is not checked about it

**Rendered 23 Aug with Kokoro-82M**, voice `bf_emma`, British English, speed 1.0. The
master is `docs/video/narration/narration.m4a`; per-beat WAVs and the QC samples are
regenerated rather than committed, because ten megabytes of lossless audio in a repository
is the kind of surprise `SUBMISSION.md` phase 1.5 tells you to find before a push and not
after.

```bash
python3 scripts/video_narration.py --phonemes        # what each patched word becomes
python3 scripts/video_narration.py --verify          # check each patch against its defect
python3 scripts/video_narration.py --qc              # pronunciation variants, side by side
python3 scripts/video_narration.py --write-timings   # render, measure, update this table
python3 scripts/video_captions.py                    # then rebuild the cues from that
```

**The render is seeded and bit-identical.** Kokoro samples, so an unseeded render gives the
same durations to the millisecond and a different waveform every time. Seeded on 1729, the
seed `config.yaml` already uses, re-rendering reproduces the committed file exactly, which
is what makes it diffable rather than noise.

It needs Python 3.12 or older: a spaCy dependency of the phoneme stack does not build on
3.13. `uv venv --python 3.12` then `uv pip install kokoro soundfile` is the whole setup,
plus a system `espeak-ng`. None of it is in `requirements.txt` and none of it ships;
`CITATIONS.md` section 7 records every component and its licence.

**Four pronunciations are patched**, because the model has never seen Shona and reads the
project's own name wrong:

| word | unpatched | patched | syllables, want / was / now | verdict |
|---|---|---|---|---|
| Mhizha | `ˈɛmhˈɪʒə` | `mˈiːʒə` | 2 / **3** / 2 | fixes a defect: a vowel was inserted before the m |
| AGRITEX | `ˌAʤˌiːˌɑːˌItˌiːˌiːˈɛks` | `ˈaɡɹɪtɛks` | 3 / **7** / 3 | fixes a defect: spelled out letter by letter |
| Qwen | `kjˈuːwˈɛn` | `kwˈɛn` | 1 / **2** / 1 | fixes a defect: Q read as its letter name |
| Mashonaland | `məʃˈQnəland` | `mˌaʃˈQnəland` | 4 / 4 / 4 | **preference, not a defect** |

`--verify` produces that table. The syllable count is exact rather than estimated, because
it is counted off the phoneme string and not off the waveform, and it happens to be the
precise shape of the failure this block exists for: a word gains syllables when letters get
spelled out or a vowel gets inserted. Three of the four patches remove a countable defect
and the check would fail the build if one stopped doing so.

**The fourth does not, and it is the one to listen to first.** Both forms of Mashonaland
are four syllables; the patch changes vowel quality only. It is kept because the name is
Zimbabwean and the schwa is the anglicisation, but that is a judgement rather than a
correction, and the evidence is mildly against it: read back by an ASR model the patched
form comes out as two words, "Mashona land", where the unpatched one stays a single word.
`--qc` renders both. Reverting is deleting one line.

**What was checked, and what was not.** Measured: no clipping anywhere, peak 0.78, no DC
offset, no truncated cue, every phoneme validated against the voice's vocabulary before
rendering, and every patch checked against the defect it claims to fix. An independent
speech-recognition model was asked what it heard, unpatched against patched, and it
confirms AGRITEX went from seven spelled-out letters to a word and Qwen from a letter name
to "kwen".

**None of that is hearing it, and Mhizha is the proof.** The name was settled on 23 Aug by
listening, and it went against the analysis. The earlier `mˈhiːʒə` was argued from Shona
phonology, where <mh> is a breathy-voiced m rather than an m followed by an h. That is true
about Shona and was wrong about this: rendered, it puts an audible vowel between the two.
**`mˈiːʒə`, the plain m, is the one that sounds like the word.**

Nothing automatic could have caught that. The syllable count passes both candidates at two.
The ASR pass returned "Mahisya" for one and "Miese" for the other, and neither is the word;
asked to transcribe a third candidate it returned "Amnesia". An ASR model spells an
unfamiliar proper noun by analogy with words it knows, so it is competent to tell an acronym
from seven spelled-out letters and not competent to judge a Shona name. The listening step
is not a formality on top of the checks. It is the only thing that decided this one.

**Still open: Mashonaland.** `--qc` renders both forms. Changing it is a one-line edit to
`PRONUNCIATIONS` then a re-render. The rejected Mhizha candidates stay renderable too, so
the choice can be re-heard rather than taken on trust.

**Note the qc file numbering follows the list order**, so it moves when a choice is made:
`qc-mhizha-1` is now the one in use. Read the label `--qc` prints, not the number.

**Listen to the whole thing once before it is cut**, not only the four names.

## What not to do

- **Do not speed up the terminal.** If generation is slow, say so; the judge-experienced
  latency question is a real finding of this project, not something to hide with an edit.
- **Do not stage a better answer.** The placeholder corpus produces mediocre extractive
  answers, and beat 2's qualifier is what makes that honest instead of disappointing.
- **Do not read the architecture diagram aloud.** Two minutes buys roughly 290 words. Spend
  them on the farmer, the refusal, and the abstention.

## Open before recording

Both original blockers are cleared.

- **O-02, the closing card.** Filled 19 Aug. Details above.
- **The selected model.** Decided 22 Aug: Qwen3.5 2B, template-baked. Beat 6 names it.

What remains is not a blocker but is worth deciding before the take:

- **Captions: done, 22 Aug ~21:50Z.** `docs/video/captions.vtt`, WebVTT, 28 cues tiling 0:00 to
  1:55. Upload it alongside the video; every host that takes a caption file takes this one.

  It is **generated from the beat table above** by `python3 scripts/video_captions.py`, not
  written out, because a hand-typed caption file is a second copy of the narration that can
  drift from the first, and a caption disagreeing with the audio is worse than none: the
  viewer without sound reads the version nobody checked. Same reasoning as the CLI captures
  being generated rather than pasted. `--check` fails if the committed file is stale against
  the beat sheet, and the generator refuses outright if a digit ever appears in a narration
  cell, since a spoken number cannot carry its caveat or be corrected after upload.

  **If you change a word of narration or a beat boundary, re-run it before recording.**

- **Whether beat 6 mentions the blind read at all. Still open, and this document has been
  contradicting itself about it.** The verbatim narration in the beat sheet *keeps* the
  clause; the note here used to say cut it. Both cannot be right on the day, so here is the
  arithmetic instead of the advice:

  | beat 6 | words | over 16s |
  |---|---|---|
  | as written, with "chosen by reading transcripts blind" | 41 | **154 wpm**, the fastest beat in the video |
  | with that clause cut | 36 | 135 wpm, the most relaxed |

  Cutting it buys the beat almost twenty words per minute, and it is the only beat above
  150. Keeping it says the most interesting thing about the selection in five words. It is
  a judgement call about the take, not a correctness question, and it belongs to whoever
  reads the script aloud. **Decide it before the take, not during**, and re-run
  `scripts/video_captions.py` if it is cut.
