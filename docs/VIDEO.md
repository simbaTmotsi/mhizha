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
and 7. Every beat is now between 140 and 154 wpm, **no word of narration changed**, and the
total is still 279 words over 1:55.

| # | Time | On screen | Spoken, verbatim |
|---|---|---|---|
| 1 | 0:00-0:18 | A field, or a still of one. Then the terminal. | "A farmer in Mashonaland is deciding what to plant this week. The nearest extension officer is a bus ride away, and there is no signal in the field. An assistant that needs a network is not there at the moment the decision gets made." |
| 2 | 0:18-0:36 | `mhizha ask` running, answer appearing | "Mhizha runs entirely offline, on a mid-range Android phone. It answers practical agronomy questions from a curated corpus, cites what it used, and says so when it cannot help. The pipeline is real. The agronomy is not sourced yet, and we say that plainly." |
| 3 | 0:36-0:53 | Capture 01, sources table highlighted | "Every claim carries a passage, and every passage names its source, its publisher and the date it was refreshed. Those placeholder banners are real. This corpus holds no agronomic content, and the system tells the farmer that instead of sounding authoritative." |
| 4 | 0:53-1:15 | Capture 03. Type the question in full. | "Ask it how much to spray, and it refuses. A dose that is not written, word for word, in a passage a human has signed off is never emitted. Not as an estimate, not as a typical figure. A wrong spray rate destroys a season, or harms the person holding the sprayer." |
| 5 | 1:15-1:30 | Capture 02, the abstention panel | "Below its confidence threshold, the model is not called at all. It says what it does not know, asks the one question that would unblock it, and sends the farmer to their local AGRITEX officer." |
| 6 | 1:30-1:46 | The profiler, or REPORT section 2.4 | "The competition profiles a bare model file, so none of this code runs while judges are scoring. We ship Qwen three point five, two billion, chosen by reading transcripts blind, with our safety posture baked into the model's own chat template." |
| 7 | 1:46-1:55 | `python3 scripts/report_figures.py`, BLOCKED lines visible | "A number that cannot be traced to a run fails our build. Where we could not measure something, the report says so." |

**Closing card:** Mhizha. Simbarashe Timothy Motsi. team_id `mhizha`. github.com/simbaTmotsi.

**On beat 6, say the model name aloud as words**, not as a filename. "Qwen three point five, two billion" is what a listener can follow; `qwen3.5-2b-q4_k_m` is not.

## Before you record: the machine has to be able to show beat 4

**Checked on the laptop, 22 Aug. Without this the strongest beat shows the wrong screen.**

`config.yaml` sets `embedder.allow_hash_fallback: true`, and a fresh clone has no embedder
weights, so the CLI comes up on the deterministic hash embedder without saying anything at
the prompt. It runs. It also retrieves differently, and beat 4 is where that shows: on the
fallback the agrochemical question **abstains** (top1 0.155) instead of answering with the
chemical-safety banner and no dose (top1 0.467). Beat 4 would then be visually identical to
beat 5, while the narration says the system refuses to give a rate.

One command tells you which one you are on:

```bash
PYTHONPATH=src python3 -m mhizha doctor | grep 'embedder weights'
# want: embedder weights: present
# not:  embedder weights: absent, hash fallback active
```

If it is absent, install the build-time dependency and save the weights as `README.md`
describes, then rebuild the index:

```bash
pip install sentence-transformers
python3 -c "from sentence_transformers import SentenceTransformer; \
  SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2').save('models/embedder/all-MiniLM-L6-v2')"
PYTHONPATH=src python3 -m mhizha embed && PYTHONPATH=src python3 -m mhizha index
```

Verified on 22 Aug: with the weights present, `make captures` reproduces `01`, `02` and
`03` byte for byte against the shipped assets, which is the check that the machine in front
of you shows what the submission claims.

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
first and `data/index/mhizha.db` ships as `data/index…`. The committed captures are the
correct ones.

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
3. **Voiceover last**, against the cut, so the pacing follows the footage rather than
   forcing it.

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

- **Captions**, for accessibility and for judges watching without sound.
- **Whether beat 6 mentions the blind read at all.** It is the most interesting thing in
  the selection and it is one clause. It is also the clause most likely to need a second
  sentence to land, and there is no room for a second sentence. Cut it rather than rush it.
