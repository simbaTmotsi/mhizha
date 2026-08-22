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
the submitter details are filled. Narration is ~280 words, which is 1:55 at an unhurried
145 words per minute. **No figure is spoken anywhere in it**, deliberately: a number in a
video cannot carry its caveat and cannot be corrected after upload, so the report keeps the
numbers and the video keeps the argument.

| # | Time | On screen | Spoken, verbatim |
|---|---|---|---|
| 1 | 0:00-0:15 | A field, or a still of one. Then the terminal. | "A farmer in Mashonaland is deciding what to plant this week. The nearest extension officer is a bus ride away, and there is no signal in the field. An assistant that needs a network is not there at the moment the decision gets made." |
| 2 | 0:15-0:32 | `mhizha ask` running, answer appearing | "Mhizha runs entirely offline, on a mid-range Android phone. It answers practical agronomy questions from a curated corpus, cites what it used, and says so when it cannot help. The pipeline is real. The agronomy is not sourced yet, and we say that plainly." |
| 3 | 0:32-0:55 | Capture 01, sources table highlighted | "Every claim carries a passage, and every passage names its source, its publisher and the date it was refreshed. Those placeholder banners are real. This corpus holds no agronomic content, and the system tells the farmer that instead of sounding authoritative." |
| 4 | 0:55-1:18 | Capture 03. Type the question in full. | "Ask it how much to spray, and it refuses. A dose that is not written, word for word, in a passage a human has signed off is never emitted. Not as an estimate, not as a typical figure. A wrong spray rate destroys a season, or harms the person holding the sprayer." |
| 5 | 1:18-1:34 | Capture 02, the abstention panel | "Below its confidence threshold, the model is not called at all. It says what it does not know, asks the one question that would unblock it, and sends the farmer to their local AGRITEX officer." |
| 6 | 1:34-1:48 | The profiler, or REPORT section 2.4 | "The competition profiles a bare model file, so none of this code runs while judges are scoring. We ship Qwen three point five, two billion, chosen by reading transcripts blind, with our safety posture baked into the model's own chat template." |
| 7 | 1:48-1:55 | `python3 scripts/report_figures.py`, BLOCKED lines visible | "A number that cannot be traced to a run fails our build. Where we could not measure something, the report says so." |

**Closing card:** Mhizha. Simbarashe Timothy Motsi. team_id `mhizha`. github.com/simbaTmotsi.

**On beat 6, say the model name aloud as words**, not as a filename. "Qwen three point five, two billion" is what a listener can follow; `qwen3.5-2b-q4_k_m` is not.

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

Both original blockers are cleared.

- **O-02, the closing card.** Filled 19 Aug. Details above.
- **The selected model.** Decided 22 Aug: Qwen3.5 2B, template-baked. Beat 6 names it.

What remains is not a blocker but is worth deciding before the take:

- **Captions**, for accessibility and for judges watching without sound.
- **Whether beat 6 mentions the blind read at all.** It is the most interesting thing in
  the selection and it is one clause. It is also the clause most likely to need a second
  sentence to land, and there is no room for a second sentence. Cut it rather than rush it.
