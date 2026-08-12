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

## Beat sheet

| # | Time | Beat | On screen | Spoken |
|---|---|---|---|---|
| 1 | 0:00-0:15 | The user, not the tech | A field, or a still of one. Then the terminal. | The problem: a farmer deciding what to plant, with no connectivity at the moment the decision is made. An assistant that needs a network is not available when it matters. |
| 2 | 0:15-0:30 | What it is | `mhizha ask` running, answer appearing | One sentence on what Mhizha is: an offline agronomy co-pilot for a mid-range Android phone. Then the honest qualifier: the pipeline is real, the agronomy is not sourced yet. |
| 3 | 0:30-0:55 | The three things agronomy forces | Capture 01, sources table highlighted | Grounded and cited: every claim carries a passage, every passage names its source and refresh date. |
| 4 | 0:55-1:15 | Refusal is the feature | Capture 03, the safety notice | The dosage gate. A rate that is not verbatim in a validated passage is never emitted, in any phrasing. A wrong spray rate destroys a season or harms the person applying it. |
| 5 | 1:15-1:30 | Willing to not answer | Capture 02, the abstention panel | Below the confidence threshold the model is not called at all. It says what it does not know, asks one clarifying question, and refers to a local AGRITEX officer. |
| 6 | 1:30-1:45 | The competition finding | The profiler, or the report section | What the profiler actually scores is the bare model file, not our code, so our retrieval and safety work is the evidence rather than the measured thing. The one channel into a judge's session is the chat template we bake at download. |
| 7 | 1:45-1:55 | Close on the discipline | `report_figures.py` output showing BLOCKED lines | Close on the honesty of the measurement work: numbers that cannot be sourced are refused by the build, and the report says what is missing and why. |

---

## What to record, and in what order

Record in this order so a re-take of the hardest beat does not invalidate the others.

1. **Terminal captures first.** `python3 scripts/capture_cli.py --list` names the four
   commands. Record them live rather than showing the saved SVGs, so the timing is real.
   Beat 4 needs the agrochemical question typed in full, because seeing the question is
   what makes the refusal land.
2. **`python3 scripts/report_figures.py`** for beat 7. Its BLOCKED section is the strongest
   thirty seconds of evidence in the project and needs no narration beyond one line.
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

- **O-02.** The closing card needs the team name and submitter details, which are still
  `TODO_*` in `metadata.json`.
- **Selected model.** Beat 6 currently names no candidate, and should not until the
  selection set is resolved. If the model is chosen before recording, add one clause; if
  not, the beat works as written.
- **Captions.** Worth adding for accessibility and for judges watching without sound.
