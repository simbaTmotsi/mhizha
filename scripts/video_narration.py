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

# Kokoro samples, so an unseeded render gives the same durations to the millisecond and a
# different waveform every time. Seeded it is bit-identical, which is what a generated
# asset has to be if regenerating it is going to be diffable rather than noise. 1729 is
# the seed config.yaml already uses; there is no reason for this project to have two.
# Set per clip, not once per run, so a single beat can be re-rendered on its own.
SEED = 1729

# ---------------------------------------------------------------- pronunciation patches
#
# Phonemes are misaki's British set. The vowel letters are its own shorthand:
#   A = /eɪ/    I = /aɪ/    Q = /əʊ/    W = /aʊ/    Y = /ɔɪ/
# Stress marks are ˈ primary and ˌ secondary. Every entry is checked against GB_VOCAB
# before anything renders.
#
# Each entry records what the G2P produces UNPATCHED and how many syllables the word
# actually has, because those two together are a check rather than an opinion: counting
# vowels in a phoneme string is exact, and the failure this whole block exists to fix is a
# word coming out with the wrong number of syllables because letters were spelled out or a
# vowel was inserted. `--verify` runs that count. See VOWELS and verify().
VOWELS = set("AIQWYaɑɒɔəɛɜɪʊʌiu")

PRONUNCIATIONS = {
    # Shona, "craftsman" or "one who is skilled". The Shona <mh> is a breathy-voiced m,
    # one sound and not two. Unpatched the G2P inserts a vowel before it and says
    # "EM-hizha" in three syllables, which is wrong in a way that would be obvious to
    # anyone the project is named for.
    "mhizha": {
        "phonemes": "mˈhiːʒə",
        "was": "ˈɛmhˈɪʒə",
        "syllables": 2,
        "why": "leading m was read as the letter name, adding a syllable",
    },
    # The province, and the first word a listener hears in beat 1. Unpatched the first
    # syllable reduces to a schwa, "muh-SHOW-na-land"; a Zimbabwean says "mash-OH-na-land"
    # with the vowel intact.
    #
    # THIS ONE FIXES NO COUNTABLE DEFECT and is the weakest of the four. Both forms are
    # four syllables; the patch changes vowel quality only, which is a preference rather
    # than a correction, and the ASR round-trip in --verify mildly prefers the unpatched
    # form because the fuller vowel reads as a word boundary ("Mashona land"). Kept
    # because the name is Zimbabwean and the reduced vowel is the anglicisation. It is
    # the first thing to listen to, and reverting it is deleting one line.
    "mashonaland": {
        "phonemes": "mˌaʃˈQnəland",
        "was": "məʃˈQnəland",
        "syllables": 4,
        "why": "PREFERENCE, not a defect: first vowel reduced to a schwa",
    },
    # Agricultural, Technical and Extension Services. An acronym said as a word by every
    # farmer and officer who deals with it. Unpatched it is spelled out letter by letter,
    # seven syllables where the word has three, inside a fourteen-second beat.
    "agritex": {
        "phonemes": "ˈaɡɹɪtɛks",
        "was": "ˌAʤˌiːˌɑːˌItˌiːˌiːˈɛks",
        "syllables": 3,
        "why": "acronym was spelled out, seven syllables instead of three",
    },
    # The selected model. Unpatched it becomes "cue-wen", reading the Q as its letter
    # name. English technical usage is "kwen". Not one of the three names asked for,
    # patched because beat 6 says it aloud and it is the model this submission ships.
    "qwen": {
        "phonemes": "kwˈɛn",
        "was": "kjˈuːwˈɛn",
        "syllables": 1,
        "why": "Q was read as the letter name, two syllables instead of one",
    },
}

# Rendered by --qc so the two calls a count cannot make get made by ear. The first entry
# of each list is what PRONUNCIATIONS uses. The "heard" note is what whisper small.en made
# of it in --verify, recorded because it is evidence and not because it is a verdict:
# Whisper spells an unfamiliar proper noun by analogy with words it knows.
#
# Also tried and dropped, so nobody re-runs them: ˈmiːʒə was transcribed "Amnesia", and
# mhˈiːʒə lost the m entirely and came back as "He's a".
QC_VARIANTS = {
    "mhizha": [
        ("mˈhiːʒə", 'in use. breathy m, nearest the Shona <mh>. heard "Mahisya"'),
        ("mˈiːʒə", 'plain m, the anglicised "MEE-zha". heard "Miese"'),
        ("mˈɪʒə", 'short i, "MIH-zha". heard "Mijo"'),
    ],
    # This pair is the real question, and it is patched versus not patched. The count says
    # the patch fixes nothing; the ASR mildly prefers the unpatched form because the fuller
    # first vowel reads as a word boundary. Neither settles whether a Zimbabwean place name
    # should carry the anglicised schwa.
    "mashonaland": [
        ("mˌaʃˈQnəland", 'in use. full first vowel, "mash-OH-na-land". heard "Mashona land"'),
        ("məʃˈQnəland", 'unpatched. reduced first vowel, "muh-SHOW-na-land". heard "Machonaland"'),
    ],
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

    patches = {word: entry["phonemes"] for word, entry in PRONUNCIATIONS.items()}
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

    import torch

    torch.manual_seed(SEED)
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

    lines = [f"# Kokoro narration, voice {voice}, speed {speed}, {SAMPLE_RATE} Hz mono, "
             f"seed {SEED}",
             "# Generated by scripts/video_narration.py. Durations are measured, not set.",
             "#", "# beat  seconds  cues"]
    for beat in rendered:
        lines.append(f"  {beat['number']}      {beat['seconds']:6.3f}  {len(beat['cues']):4d}")
    total = sum(b["seconds"] for b in rendered) + GAP_BETWEEN_BEATS * (len(rendered) - 1)
    peak = max(c["peak"] for b in rendered for c in b["cues"])
    clipped = max(c["clipped"] for b in rendered for c in b["cues"])
    lines += ["#", f"# total {total:.3f} s including {GAP_BETWEEN_BEATS} s between beats"]
    # Levels are a threshold, not a figure. Printing peak to two decimals per beat made
    # this file churn on every render for no meaning; what matters is that nothing clips
    # and there is headroom, and both are pass or fail.
    lines += [f"# peak {peak:.2f}, clipped samples {clipped:.4%}: "
              f"{'PASS' if peak < 0.99 and clipped == 0 else 'FAIL'}"]
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


def syllables(phonemes: str) -> int:
    """Syllable count from a phoneme string: one per vowel nucleus.

    Exact, not estimated. Length marks and stress marks are not nuclei, and a doubled
    vowel letter inside a long vowel (iː, uː) is one nucleus because the ː follows it.
    """
    count, previous = 0, ""
    for character in phonemes:
        if character in VOWELS and previous not in VOWELS:
            count += 1
        previous = character
    return count


def transcribe_available() -> bool:
    try:
        import scipy.signal  # noqa: F401
        import whisper  # noqa: F401
    except ImportError:
        return False
    return True


def transcribe(audio):
    """What an independent listener model hears. Corroboration, never the verdict.

    Whisper spells a proper noun it has never seen by analogy with words it has, so it is
    competent to tell an acronym from seven spelled-out letters and incompetent to judge
    a Shona name. Read it that way.
    """
    import numpy as np
    import whisper
    from scipy.signal import resample_poly

    resampled = resample_poly(audio.astype(np.float64), 16_000, SAMPLE_RATE)
    model = whisper.load_model("small.en")
    said = model.transcribe(resampled.astype(np.float32), language="en",
                            fp16=False, temperature=0.0)
    return said["text"].strip()


def verify(voice: str, speed: float) -> int:
    """Check every patch against the defect it claims to fix.

    The syllable count is the real test and it needs no audio: the failure mode here is a
    word gaining syllables because letters were spelled out or a vowel was inserted, and
    that is countable in the phoneme string. The ASR pass is corroboration for the cases
    where a count cannot see the difference.
    """
    failures = []
    print(f"{'word':13} {'expected':>8} {'unpatched':>10} {'patched':>8}   verdict")
    for word, entry in PRONUNCIATIONS.items():
        want = entry["syllables"]
        before, after = syllables(entry["was"]), syllables(entry["phonemes"])
        if after != want:
            verdict = "FAILS: patched count is wrong"
            failures.append(word)
        elif before == want:
            verdict = "preference only, no countable defect"
        else:
            verdict = f"fixes {before - want:+d} syllable defect"
        print(f"{word:13} {want:>8} {before:>10} {after:>8}   {verdict}")

    if not transcribe_available():
        print("\nASR corroboration skipped: pip install openai-whisper scipy to run it.")
    else:
        print("\nHeard back by whisper small.en, unpatched vs patched:")
        for word, entry in PRONUNCIATIONS.items():
            sentence = next((c for beat in beats_source.read_beats(beats_source.SOURCE)
                             for c in beats_source.split_cue(beat["spoken"])
                             if word in c.lower()), word.capitalize() + ".")
            off = build_pipeline(voice, {word: entry["was"]})
            on = build_pipeline(voice)
            print(f"  {word}")
            print(f"    was -> {transcribe(say(off, sentence, voice, speed)[0])}")
            print(f"    now -> {transcribe(say(on, sentence, voice, speed)[0])}")

    print("\nNeither check hears anything. They prove a patch changed what it claimed to "
          "change;\nwhether the result sounds right is still --qc and a person.")
    if failures:
        print(f"\nFAILED: {', '.join(failures)}", file=sys.stderr)
        return 1
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Render the narration with Kokoro.")
    parser.add_argument("--voice", default=DEFAULT_VOICE)
    parser.add_argument("--speed", type=float, default=1.0)
    parser.add_argument("--phonemes", action="store_true",
                        help="print what every patched word becomes, and stop")
    parser.add_argument("--verify", action="store_true",
                        help="check every patch against the defect it claims to fix")
    parser.add_argument("--qc", action="store_true",
                        help="render pronunciation variants side by side, and stop")
    parser.add_argument("--write-timings", action="store_true",
                        help="write the measured beat boundaries back into docs/VIDEO.md")
    args = parser.parse_args()

    try:
        if args.phonemes:
            pipeline = build_pipeline(args.voice)
            print(f"{'word':14} {'phonemes':24} as read back by the G2P")
            for word, entry in PRONUNCIATIONS.items():
                _, actual = say(pipeline, word.capitalize(), args.voice, args.speed)
                print(f"{word:14} {entry['phonemes']:24} {actual}")
            return 0

        if args.verify:
            return verify(args.voice, args.speed)

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
