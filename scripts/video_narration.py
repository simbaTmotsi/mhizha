#!/usr/bin/env python3
"""Generate the submission video's narration with Kokoro, and measure what it made.

BUILD TIME. Network on first run only, to fetch the Kokoro weights and the spaCy tagger
misaki uses. Nothing here ships to a device and nothing under src/mhizha imports it.

WHAT THIS IS FOR
----------------
`docs/VIDEO.md` holds the narration verbatim. `scripts/video_captions.py` turns it into
caption cues. This turns the same cells into speech, in the same units, so the audio, the
captions and the beat sheet cannot disagree about what is said or when.

TIMINGS COME OUT, NOT IN
------------------------
The beat boundaries in `docs/VIDEO.md` began as arithmetic: words divided by an assumed
145 per minute. That is a planning estimate and it was never a measurement. This reads the
real duration of every clip it renders and writes the timings back out, so the cue windows
follow the audio rather than the audio being stretched to fit a guess. Nothing here
time-stretches; a clip that runs long moves the boundary instead of being squeezed, because
a squeezed voice is audibly a squeezed voice.

PRONUNCIATION
-------------
Kokoro reaches English text through a grapheme-to-phoneme pass that has never seen Shona
and does not know this project's proper nouns. Left alone it says "EM-hizha", and it spells
AGRITEX out letter by letter. Those are patched below, in the phoneme alphabet misaki uses,
with the reason recorded beside each one. See PRONUNCIATIONS.

Every patch is validated against the voice's own vocabulary before a single sample is
rendered, because a phoneme the model cannot say is a silent corruption rather than an
error.

WHAT THIS CANNOT DO
-------------------
It cannot tell you whether the result sounds right. Duration, clipping, silence and
truncation are measured here; everything about the *sound* of a name in a language the
author speaks and this script does not needs a person and a pair of headphones. Run
`--qc` to render the ambiguous cases side by side for that listen.

Usage:
    python3 scripts/video_narration.py --phonemes   # what every patched word becomes
    python3 scripts/video_narration.py --qc         # render pronunciation variants to compare
    python3 scripts/video_narration.py              # render the narration and measure it
    python3 scripts/video_narration.py --write-timings   # ... and update docs/VIDEO.md
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))

import video_captions as beats_source  # noqa: E402

OUT = REPO / "docs" / "video" / "narration"
SAMPLE_RATE = 24_000

# British English. The narration is written in British spelling ("fertiliser", "sourced")
# and the closing card is a Zimbabwean submitter; RP is the nearer neutral of the two
# accents Kokoro ships. There is no African English voice in the model.
LANG_CODE = "b"
DEFAULT_VOICE = "bf_emma"

# Rendered speech is not metronomic, so a gap that reads as a pause on the page has to
# exist in the audio too. Both are measured into the published timings rather than assumed
# away: a cue starts when the previous clip ends plus this.
GAP_WITHIN_BEAT = 0.12
GAP_BETWEEN_BEATS = 0.35

# ---------------------------------------------------------------- pronunciation patches
#
# Phonemes are misaki's British set. The vowel letters are its own shorthand:
#   A = /eɪ/    I = /aɪ/    Q = /əʊ/    W = /aʊ/    Y = /ɔɪ/
# Stress marks are ˈ primary and ˌ secondary. Every entry is checked against GB_VOCAB at
# load time.
#
# The "was" column is what Kokoro produces unpatched, recorded so a future reader can tell
# a deliberate patch from a default.
PRONUNCIATIONS = {
    # Shona, "craftsman" or "one who is skilled". The Shona <mh> is a breathy-voiced m,
    # one sound and not two. Unpatched, the G2P treats the leading M as a spelled-out
    # letter and says "EM-hizha", which is wrong in a way that would be obvious to anyone
    # the project is named for.
    #   was: ˈɛmhˈɪʒə          this: m + long ee + zh + schwa, "MHEE-zha"
    "mhizha": "mˈhiːʒə",

    # The province, and the first word a listener hears in beat 1. Unpatched the first
    # syllable reduces to a schwa, "muh-SHOW-na-land". It is "mash-OH-na-land".
    #   was: məʃˈQnəland
    "mashonaland": "mˌaʃˈQnəland",

    # Agricultural, Technical and Extension Services. An acronym said as a word by every
    # farmer and officer who deals with it. Unpatched it is spelled out, letter by letter,
    # for seven syllables inside a fourteen-second beat.
    #   was: ˌAʤˌiːˌɑːˌItˌiːˌiːˈɛks
    "agritex": "ˈaɡɹɪtɛks",

    # The selected model. Unpatched it becomes "cue-wen", reading the Q as its letter name.
    # English technical usage is "kwen". Not one of the three names asked for, patched
    # because beat 6 says it aloud and it is the model this submission ships.
    #   was: kjˈuːwˈɛn
    "qwen": "kwˈɛn",
}

# Rendered by --qc so the call can be made by ear rather than by argument. The first entry
# of each pair is what PRONUNCIATIONS uses.
QC_VARIANTS = {
    "mhizha": [("mˈhiːʒə", "breathy m, closer to the Shona <mh>"),
               ("mˈiːʒə", "plain m, 'MEE-zha', the anglicised form")],
    "mashonaland": [("mˌaʃˈQnəland", "mash-OH-na-land"),
                    ("mˌaʃˈQnəlˌand", "same, with the final syllable stressed")],
}


class NarrationError(RuntimeError):
    """Raised when the narration cannot be rendered honestly."""


def espeak_paths() -> None:
    """Point misaki at a working espeak-ng.

    The wheel-bundled loader hardcodes the path of the machine it was built on, so on a
    host with its own espeak-ng the bundled one fails on a missing phontab. Prefer an
    explicit override, then the system install, then whatever the wheel shipped.
    """
    import espeakng_loader

    library = os.environ.get("ESPEAK_LIBRARY")
    data = os.environ.get("ESPEAK_DATA_PATH")
    for prefix in ("/opt/homebrew", "/usr/local", "/usr"):
        if library and data:
            break
        candidate_lib = Path(prefix) / "lib" / "libespeak-ng.dylib"
        candidate_so = Path(prefix) / "lib" / "libespeak-ng.so"
        candidate_data = Path(prefix) / "share" / "espeak-ng-data"
        found = candidate_lib if candidate_lib.exists() else (
            candidate_so if candidate_so.exists() else None)
        if found and candidate_data.is_dir():
            library, data = library or str(found), data or str(candidate_data)
    if library and data:
        espeakng_loader.get_library_path = lambda: library
        espeakng_loader.get_data_path = lambda: data


def build_pipeline(voice: str, extra: dict[str, str] | None = None):
    espeak_paths()
    from kokoro import KPipeline
    from misaki.en import GB_VOCAB

    patches = dict(PRONUNCIATIONS)
    patches.update(extra or {})
    for word, phonemes in patches.items():
        unknown = sorted({c for c in phonemes if c not in GB_VOCAB})
        if unknown:
            raise NarrationError(
                f"pronunciation for {word!r} uses {unknown}, which the voice cannot say. "
                f"A phoneme outside the vocabulary is a silent corruption, not an error.")

    pipeline = KPipeline(lang_code=LANG_CODE)
    lexicon = pipeline.g2p.lexicon
    for word, phonemes in patches.items():
        lexicon.golds[word] = phonemes
        lexicon.golds[word.capitalize()] = phonemes
        lexicon.golds[word.upper()] = phonemes
    _ = voice
    return pipeline


def say(pipeline, text: str, voice: str, speed: float):
    """One contiguous clip for one cue, plus the phonemes it was actually read from."""
    import numpy as np

    chunks, phonemes = [], []
    for result in pipeline(text, voice=voice, speed=speed, split_pattern=None):
        if result.audio is None:
            raise NarrationError(f"no audio produced for {text!r}")
        chunks.append(result.audio.detach().cpu().numpy())
        phonemes.append(result.phonemes)
    return np.concatenate(chunks), " ".join(phonemes)


def measure(samples) -> dict[str, float]:
    """Objective checks. None of these is a judgement about how it sounds."""
    import numpy as np

    peak = float(np.max(np.abs(samples))) if len(samples) else 0.0
    loud = np.abs(samples) > 0.02
    lead = int(np.argmax(loud)) if loud.any() else len(samples)
    tail = int(len(samples) - np.argmax(loud[::-1])) if loud.any() else 0
    return {
        "seconds": len(samples) / SAMPLE_RATE,
        "peak": peak,
        "clipped": float(np.mean(np.abs(samples) >= 0.999)),
        "lead_silence": lead / SAMPLE_RATE,
        "tail_silence": (len(samples) - tail) / SAMPLE_RATE,
    }


def render(voice: str, speed: float):
    """Every cue rendered and measured, grouped by beat. No timing is assumed."""
    import numpy as np

    pipeline = build_pipeline(voice)
    beats = beats_source.read_beats(beats_source.SOURCE)
    beats_source.assert_no_figures(beats)

    rendered = []
    for beat in beats:
        cues = []
        for text in beats_source.split_cue(beat["spoken"]):
            audio, phonemes = say(pipeline, text, voice, speed)
            cues.append({"text": text, "audio": audio, "phonemes": phonemes,
                         **measure(audio)})
        gap = np.zeros(int(GAP_WITHIN_BEAT * SAMPLE_RATE), dtype=np.float32)
        joined = cues[0]["audio"]
        for cue in cues[1:]:
            joined = np.concatenate([joined, gap, cue["audio"]])
        rendered.append({"number": beat["number"], "cues": cues, "audio": joined,
                         "seconds": len(joined) / SAMPLE_RATE})
    return rendered


def timeline(rendered) -> list[dict]:
    """Absolute cue windows, from measured durations only."""
    cursor, out = 0.0, []
    for beat in rendered:
        start = cursor
        for position, cue in enumerate(beat["cues"]):
            end = cursor + cue["seconds"]
            out.append({"beat": beat["number"], "text": cue["text"],
                        "start": cursor, "end": end})
            cursor = end + (GAP_WITHIN_BEAT if position < len(beat["cues"]) - 1 else 0.0)
        beat["start"], beat["end"] = start, cursor
        cursor += GAP_BETWEEN_BEATS
    return out


def write_timeline(cues) -> None:
    """The cue windows the captions are built from, to millisecond precision.

    The beat table in docs/VIDEO.md is rounded to the second because it is a beat sheet a
    person reads. Captions are read by a player, so they get the measurement itself.
    """
    lines = ["# Measured cue windows. Written by scripts/video_narration.py.",
             "# seconds_start seconds_end beat text",
             "# The text must match docs/VIDEO.md verbatim; video_captions.py checks it."]
    for cue in cues:
        lines.append(f"{cue['start']:.3f}\t{cue['end']:.3f}\t{cue['beat']}\t{cue['text']}")
    (OUT / "TIMINGS.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_audio(rendered, voice: str, speed: float) -> None:
    import numpy as np
    import soundfile as sf

    OUT.mkdir(parents=True, exist_ok=True)
    full = []
    for beat in rendered:
        sf.write(OUT / f"beat-{beat['number']}.wav", beat["audio"], SAMPLE_RATE)
        full.append(beat["audio"])
        full.append(np.zeros(int(GAP_BETWEEN_BEATS * SAMPLE_RATE), dtype=np.float32))
    sf.write(OUT / "narration.wav", np.concatenate(full[:-1]), SAMPLE_RATE)

    lines = [f"# Kokoro narration, voice {voice}, speed {speed}, {SAMPLE_RATE} Hz mono",
             "# Generated by scripts/video_narration.py. Durations are measured, not set.",
             "#", "# beat  seconds  peak  lead_silence  tail_silence  cues"]
    for beat in rendered:
        peak = max(c["peak"] for c in beat["cues"])
        lines.append(f"  {beat['number']}      {beat['seconds']:6.3f}  {peak:4.2f}  "
                     f"{beat['cues'][0]['lead_silence']:12.3f}  "
                     f"{beat['cues'][-1]['tail_silence']:12.3f}  {len(beat['cues']):4d}")
    total = sum(b["seconds"] for b in rendered) + GAP_BETWEEN_BEATS * (len(rendered) - 1)
    lines += ["#", f"# total {total:.3f} s including {GAP_BETWEEN_BEATS} s between beats"]
    (OUT / "MEASURED.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


def clock(seconds: float) -> str:
    return f"{int(seconds // 60)}:{int(round(seconds % 60)):02d}"


def write_timings(rendered) -> None:
    """Replace the assumed beat boundaries in docs/VIDEO.md with measured ones."""
    text = beats_source.SOURCE.read_text(encoding="utf-8")
    for beat in rendered:
        old = None
        for line in text.splitlines():
            match = beats_source.BEAT_ROW.match(line)
            if match and int(match.group(1)) == beat["number"]:
                old = f"| {match.group(2)}-{match.group(3)} |"
        new = f"| {clock(beat['start'])}-{clock(beat['end'])} |"
        if old is None:
            raise NarrationError(f"beat {beat['number']} not found in the beat table")
        head, _, tail = text.partition(old)
        text = head + new + tail
    beats_source.SOURCE.write_text(text, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Render the narration with Kokoro.")
    parser.add_argument("--voice", default=DEFAULT_VOICE)
    parser.add_argument("--speed", type=float, default=1.0)
    parser.add_argument("--phonemes", action="store_true",
                        help="print what every patched word becomes, and stop")
    parser.add_argument("--qc", action="store_true",
                        help="render pronunciation variants side by side, and stop")
    parser.add_argument("--write-timings", action="store_true",
                        help="write the measured beat boundaries back into docs/VIDEO.md")
    args = parser.parse_args()

    try:
        if args.phonemes:
            pipeline = build_pipeline(args.voice)
            print(f"{'word':14} {'phonemes':24} as read back by the G2P")
            for word in PRONUNCIATIONS:
                _, actual = say(pipeline, word.capitalize(), args.voice, args.speed)
                print(f"{word:14} {PRONUNCIATIONS[word]:24} {actual}")
            return 0

        if args.qc:
            import soundfile as sf
            OUT.mkdir(parents=True, exist_ok=True)
            for word, variants in QC_VARIANTS.items():
                for index, (phonemes, why) in enumerate(variants, start=1):
                    pipeline = build_pipeline(args.voice, {word: phonemes})
                    sentence = next(c for b in beats_source.read_beats(beats_source.SOURCE)
                                    for c in beats_source.split_cue(b["spoken"])
                                    if word in c.lower())
                    audio, _ = say(pipeline, sentence, args.voice, args.speed)
                    name = f"qc-{word}-{index}.wav"
                    sf.write(OUT / name, audio, SAMPLE_RATE)
                    mark = "  <- in use" if index == 1 else ""
                    print(f"{name:26} {phonemes:16} {why}{mark}")
            print("\nListen to these. Duration and level are measurable here; whether a "
                  "Shona name sounds right is not.")
            return 0

        rendered = render(args.voice, args.speed)
        cues = timeline(rendered)
        write_audio(rendered, args.voice, args.speed)
        write_timeline(cues)
        total = rendered[-1]["end"]
        print(f"rendered {len(cues)} cues in {len(rendered)} beats, "
              f"{total:.2f} s measured ({clock(total)})")
        for beat in rendered:
            print(f"  beat {beat['number']}  {clock(beat['start'])}-{clock(beat['end'])}"
                  f"  {beat['seconds']:6.2f} s")
        if args.write_timings:
            write_timings(rendered)
            print(f"\nwrote measured boundaries into {beats_source.SOURCE.name}; "
                  f"now re-run scripts/video_captions.py")
        else:
            print("\n--write-timings updates docs/VIDEO.md with these boundaries.")
        return 0
    except NarrationError as problem:
        print(f"error: {problem}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
