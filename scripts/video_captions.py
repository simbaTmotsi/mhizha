#!/usr/bin/env python3
"""Generate WebVTT captions for the submission video from docs/VIDEO.md.

BUILD TIME. No network, no archive access.

WHY THIS IS GENERATED RATHER THAN WRITTEN
-----------------------------------------
`docs/VIDEO.md` holds the narration verbatim and the beat boundaries. A caption file
typed out by hand is a second copy of the same words that can drift from the first, and
a caption that disagrees with the audio is worse than no caption: a judge watching
without sound reads the version nobody checked. So the beat sheet stays the single
source and this emits from it, the same way the CLI captures are generated rather than
pasted.

The one rule it enforces on the way past: the script deliberately speaks no figure, so a
digit appearing in any narration cell is a failure here rather than a discovery on the
upload page. Spelled-out quantities ("two billion") are words and pass, which is exactly
why the beat sheet spells them out.

Usage:
    python3 scripts/video_captions.py            # write docs/video/captions.vtt
    python3 scripts/video_captions.py --check    # verify the file on disk is current
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SOURCE = REPO / "docs" / "VIDEO.md"
TARGET = REPO / "docs" / "video" / "captions.vtt"
# Written by scripts/video_narration.py from the rendered audio. When it exists the cue
# windows come from what the narration actually does; without it they are allocated by
# word count, which is a plan and says so.
MEASURED = REPO / "docs" / "video" / "narration" / "TIMINGS.txt"

# A caption line a viewer can read in the time it is on screen. Two lines at roughly
# forty characters is the broadcast convention and it is what players lay out well.
MAX_CUE_CHARS = 84

BEAT_ROW = re.compile(r"^\|\s*([1-7])\s*\|\s*(\d:\d\d)-(\d:\d\d)\s*\|([^|]*)\|(.*)\|\s*$")


class CaptionError(RuntimeError):
    """Raised when the beat sheet cannot produce an honest caption file."""


def timestamp(seconds: float) -> str:
    minutes, rest = divmod(seconds, 60)
    return f"00:{int(minutes):02d}:{rest:06.3f}"


def to_seconds(clock: str) -> int:
    minutes, seconds = clock.split(":")
    return int(minutes) * 60 + int(seconds)


def read_beats(source: Path) -> list[dict]:
    beats = []
    for line in source.read_text(encoding="utf-8").splitlines():
        match = BEAT_ROW.match(line)
        if not match:
            continue
        number, start, end, _screen, spoken = match.groups()
        spoken = spoken.strip().strip('"').strip()
        beats.append({
            "number": int(number),
            "start": to_seconds(start),
            "end": to_seconds(end),
            "spoken": spoken,
        })
    if len(beats) != 7:
        raise CaptionError(
            f"expected 7 beats in {source.name}, found {len(beats)}. The beat table "
            f"shape changed; fix the parser rather than shipping partial captions.")
    return beats


def assert_no_figures(beats: list[dict]) -> None:
    """The narration contains no number, on purpose. Prove it before emitting."""
    offenders = [f"beat {b['number']}: {d}" for b in beats
                 for d in re.findall(r"\d[\d.,]*", b["spoken"])]
    if offenders:
        raise CaptionError(
            "a digit appears in the narration, and a number spoken in a video cannot "
            "carry its caveat or be corrected after upload:\n  " + "\n  ".join(offenders))


def split_cue(text: str) -> list[str]:
    """Sentences, then long sentences split at a comma or a space near the middle."""
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]
    chunks: list[str] = []
    for sentence in sentences:
        pending = [sentence]
        while pending:
            piece = pending.pop(0)
            if len(piece) <= MAX_CUE_CHARS:
                chunks.append(piece)
                continue
            middle = len(piece) // 2
            commas = [m.end() for m in re.finditer(r",\s", piece)]
            spaces = [m.end() for m in re.finditer(r"\s", piece)]
            candidates = commas or spaces
            cut = min(candidates, key=lambda position: abs(position - middle))
            pending = [piece[:cut].strip(), piece[cut:].strip()] + pending
    return chunks


def read_measured(beats: list[dict]) -> list[tuple[float, float, str]] | None:
    """Cue windows measured from the rendered narration, or None if it has not been made.

    The text column is checked against the beat sheet word for word. A timings file that
    has drifted from the narration is the one way this could caption the wrong words with
    real-looking timings, so it is refused rather than trusted.
    """
    if not MEASURED.exists():
        return None
    rows = []
    for line in MEASURED.read_text(encoding="utf-8").splitlines():
        if line.startswith("#") or not line.strip():
            continue
        start, end, _beat, text = line.split("\t", 3)
        rows.append((float(start), float(end), text))
    spoken = " ".join(c for beat in beats for c in split_cue(beat["spoken"]))
    if " ".join(text for _, _, text in rows) != spoken:
        raise CaptionError(
            f"{MEASURED.name} does not match the narration in {SOURCE.name}. Re-run "
            f"scripts/video_narration.py; captioning stale text with measured timings "
            f"would look more trustworthy than it is.")
    return rows


def build(beats: list[dict]) -> str:
    lines = ["WEBVTT", "",
             "NOTE Generated by scripts/video_captions.py from docs/VIDEO.md.",
             "NOTE Edit the beat sheet, never this file.",
             "NOTE",
             "NOTE Narration is a synthetic voice: Kokoro-82M (hexgrad, Apache-2.0),",
             "NOTE voice bf_emma, rendered by scripts/video_narration.py. No human read",
             "NOTE this script aloud, and a viewer is entitled to know that.", ""]
    measured = read_measured(beats)
    if measured is not None:
        lines.insert(4, "NOTE Cue windows measured from the rendered audio, not estimated.")
        for index, (start, end, text) in enumerate(measured, start=1):
            lines += [str(index), f"{timestamp(start)} --> {timestamp(end)}", text, ""]
        return "\n".join(lines)
    lines.insert(4, "NOTE Cue windows allocated by word count; no audio has been rendered.")
    index = 0
    for beat in beats:
        cues = split_cue(beat["spoken"])
        weights = [len(c.split()) for c in cues]
        span = beat["end"] - beat["start"]
        total = sum(weights)
        cursor = float(beat["start"])
        for position, (cue, weight) in enumerate(zip(cues, weights)):
            index += 1
            share = span * weight / total
            end = beat["end"] if position == len(cues) - 1 else cursor + share
            lines += [str(index),
                      f"{timestamp(cursor)} --> {timestamp(end)}",
                      cue, ""]
            cursor = end
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true",
                        help="fail if the committed file is not what the beat sheet says")
    args = parser.parse_args()

    try:
        beats = read_beats(SOURCE)
        assert_no_figures(beats)
    except CaptionError as problem:
        print(f"error: {problem}", file=sys.stderr)
        return 1

    text = build(beats)
    relative = TARGET.relative_to(REPO)

    if args.check:
        if not TARGET.exists():
            print(f"error: {relative} does not exist. Run without --check.",
                  file=sys.stderr)
            return 1
        if TARGET.read_text(encoding="utf-8") != text:
            print(f"error: {relative} is stale against docs/VIDEO.md. Regenerate it.",
                  file=sys.stderr)
            return 1
        print(f"{relative} is current")
        return 0

    TARGET.parent.mkdir(parents=True, exist_ok=True)
    TARGET.write_text(text, encoding="utf-8")
    spoken = sum(len(b["spoken"].split()) for b in beats)
    print(f"wrote {relative}: {text.count(' --> ')} cues, "
          f"{spoken} words, {beats[-1]['end']}s, no figures spoken")
    return 0


if __name__ == "__main__":
    sys.exit(main())
