#!/usr/bin/env python3
"""Render the submission video from real terminal runs and the rendered narration.

BUILD TIME. No network. Nothing under src/mhizha imports this.

WHAT THIS IS, EXACTLY
---------------------
Every terminal beat is a **real execution**. The commands run in a pseudo-terminal, their
output is captured as it arrives, and the pause before it arrives is the pause the machine
actually took. Nothing is mocked and nothing is sped up: `docs/VIDEO.md` says a slow
generation is a finding of this project rather than something to hide with an edit, and the
waits in this video are the measured ones.

It is **not a screen capture.** The captured session is re-drawn as a terminal rather than
filmed, which is what makes it reproducible and what keeps a developer's desktop, home
directory and notifications out of frame. Two things in it are therefore presentation
rather than measurement, and both are stated here so nobody has to infer them:

  1. **The typing cadence is synthetic**, a fixed characters-per-second. Nothing about the
     system's behaviour is being represented by it; it is a person typing, and no person
     types at a constant rate.
  2. **Beat 1 has no field footage.** The beat sheet asks for a field or a still of one.
     There is none, and inventing an image of Zimbabwean farmland to stand behind a claim
     about Zimbabwean farmers is exactly the kind of thing this project refuses to do
     everywhere else. A title card stands in until the terminal appears.

Re-shoot any beat with a camera and a real terminal if you would rather. The audio, the
captions and the beat boundaries do not change if you do.

Usage:
    python3 scripts/video_render.py             # capture, render, encode
    python3 scripts/video_render.py --probe     # capture only, print the real timings
"""
from __future__ import annotations

import argparse
import os
import pty
import re
import select
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))

NARRATION = REPO / "docs" / "video" / "narration" / "narration.m4a"
TIMINGS = REPO / "docs" / "video" / "narration" / "TIMINGS.txt"
CAPTIONS = REPO / "docs" / "video" / "captions.vtt"
OUT = REPO / "docs" / "video" / "mhizha.mp4"

FPS = 30
WIDTH, HEIGHT = 1920, 1080
COLUMNS = 88
FONT_SIZE = 24
LINE_HEIGHT = 30
MARGIN_X, MARGIN_Y = 96, 54
FONT_PATH = "/System/Library/Fonts/Menlo.ttc"

# A person typing, not the machine. See the module docstring.
TYPING_CPS = 14.0
# Held after the last beat so the closing card is readable rather than a flash.
CLOSING_SECONDS = 4.0
GAP_BETWEEN_BEATS = 0.35

BACKGROUND = (18, 20, 26)
FOREGROUND = (222, 226, 233)
DIM = (120, 126, 138)
PROMPT = (126, 200, 160)
YELLOW = (214, 178, 96)
CYAN = (120, 190, 214)
CURSOR = (222, 226, 233)

PY = ".venv/bin/python" if (REPO / ".venv/bin/python").exists() else sys.executable

# What happens on screen, beat by beat. The command is typed, then run for real.
BEATS = {
    2: ("run", [PY, "-m", "mhizha", "ask", "when should I plant maize in Mashonaland"],
        "mhizha ask when should I plant maize in Mashonaland"),
    3: ("hold", None, None),
    4: ("run", [PY, "-m", "mhizha", "ask",
                "how much cypermethrin per litre of water for fall armyworm on maize"],
        "mhizha ask how much cypermethrin per litre of water for fall armyworm on maize"),
    5: ("run", [PY, "-m", "mhizha", "ask", "how do I prune my avocado trees in winter"],
        "mhizha ask how do I prune my avocado trees in winter"),
    6: ("run", ["cat", "competition/system_prompt.txt"],
        "cat competition/system_prompt.txt"),
    7: ("run", [PY, "scripts/report_figures.py"],
        "python3 scripts/report_figures.py"),
}

TITLE = ["Mhizha", "", "An offline agronomy assistant for smallholder farmers in Zimbabwe.",
         "It runs on the phone. It cites what it used. It refuses what it cannot source."]
CLOSING = ["Mhizha", "", "Simbarashe Timothy Motsi", "team_id  mhizha",
           "github.com/simbaTmotsi", "", "Narration: Kokoro-82M, a synthetic voice."]

SGR = re.compile(r"\x1b\[([0-9;]*)m")


class RenderError(RuntimeError):
    """Raised when the video cannot be rendered from real material."""


# ------------------------------------------------------------------ real capture

def capture(argv: list[str]) -> tuple[float, str]:
    """Run a command in a pty. Returns (seconds until output, the output).

    The wait is the machine's, measured here rather than chosen. Rich renders its panels
    in one write at the end, so a single first-byte time describes the whole beat.
    """
    env = dict(os.environ, PYTHONPATH="src", COLUMNS=str(COLUMNS), LINES="60",
               TERM="xterm-256color", HF_HUB_DISABLE_PROGRESS_BARS="1",
               TRANSFORMERS_VERBOSITY="error")
    pid, fd = pty.fork()
    if pid == 0:
        os.chdir(REPO)
        os.execvpe(argv[0], argv, env)
        os._exit(1)
    # A pty defaults to 80x24. Programs that ask the tty rather than the environment would
    # otherwise lay out for a width this render does not use.
    import fcntl
    import struct
    import termios

    fcntl.ioctl(fd, termios.TIOCSWINSZ, struct.pack("HHHH", 60, COLUMNS, 0, 0))
    started = time.monotonic()
    first, chunks = None, []
    while True:
        ready, _, _ = select.select([fd], [], [], 120)
        if not ready:
            break
        try:
            data = os.read(fd, 65536)
        except OSError:
            break
        if not data:
            break
        if first is None:
            first = time.monotonic() - started
        chunks.append(data)
    os.waitpid(pid, 0)
    if not chunks:
        raise RenderError(f"no output from {' '.join(argv)}")
    return first or 0.0, b"".join(chunks).decode("utf-8", "replace")


def to_lines(text: str) -> list[list[tuple[str, tuple[int, int, int], bool]]]:
    """Terminal text to styled lines. Only the SGR codes rich actually emits."""
    colour, bold, dim = FOREGROUND, False, False
    lines, current = [], []
    for part in re.split(r"(\x1b\[[0-9;]*m)", text.replace("\r\n", "\n").replace("\r", "")):
        if not part:
            continue
        match = SGR.fullmatch(part)
        if match:
            for code in (match.group(1) or "0").split(";"):
                if code in ("", "0"):
                    colour, bold, dim = FOREGROUND, False, False
                elif code == "1":
                    bold = True
                elif code == "2":
                    dim = True
                elif code == "33":
                    colour = YELLOW
                elif code == "36":
                    colour = CYAN
            continue
        for index, chunk in enumerate(part.split("\n")):
            if index:
                lines.append(current)
                current = []
            if chunk:
                current.append((chunk, DIM if dim else colour, bold))
    lines.append(current)
    while lines and not any(text for text, _, _ in lines[-1]):
        lines.pop()
    return [row for line in lines for row in wrap(line)]


def wrap(spans):
    """Break one logical line at the terminal width, keeping styles across the break.

    A terminal emulator wraps; this renderer draws, so without this a long line runs off
    the frame. report_figures.py prints a BLOCKED reason of about two hundred characters
    and it is the strongest thing in the video, so it has to be on screen in full.
    """
    rows, current, used = [], [], 0
    for text, colour, bold in spans:
        while text:
            room = COLUMNS - used
            if len(text) <= room:
                current.append((text, colour, bold))
                used += len(text)
                break
            cut = text.rfind(" ", 0, room + 1)
            if cut <= 0:
                cut = room
            head, text = text[:cut], text[cut:].lstrip(" ")
            if head:
                current.append((head, colour, bold))
            rows.append(current)
            current, used = [], 0
    rows.append(current)
    return rows or [[]]


# ------------------------------------------------------------------ drawing

def load_fonts():
    from PIL import ImageFont
    return (ImageFont.truetype(FONT_PATH, FONT_SIZE, index=0),
            ImageFont.truetype(FONT_PATH, FONT_SIZE, index=1))


def screen(lines, cursor_after=None, dim_except=None, fonts=None):
    """One terminal frame. `lines` is already styled; `cursor_after` is (row, col)."""
    from PIL import Image, ImageDraw

    regular, bold = fonts
    image = Image.new("RGB", (WIDTH, HEIGHT), BACKGROUND)
    draw = ImageDraw.Draw(image)
    advance = draw.textlength("M", font=regular)
    for row, spans in enumerate(lines):
        y = MARGIN_Y + row * LINE_HEIGHT
        if y > HEIGHT - MARGIN_Y:
            break
        x = MARGIN_X
        faded = dim_except is not None and not (dim_except[0] <= row <= dim_except[1])
        for text, colour, is_bold in spans:
            if faded:
                colour = tuple(int(BACKGROUND[i] + (colour[i] - BACKGROUND[i]) * 0.28)
                               for i in range(3))
            draw.text((x, y), text, font=bold if is_bold else regular, fill=colour)
            x += advance * len(text)
    if cursor_after is not None:
        row, col = cursor_after
        x = MARGIN_X + advance * col
        y = MARGIN_Y + row * LINE_HEIGHT
        draw.rectangle([x, y + 3, x + advance - 1, y + FONT_SIZE + 5], fill=CURSOR)
    return image


def card(lines, fonts):
    from PIL import Image, ImageDraw

    regular, bold = fonts
    image = Image.new("RGB", (WIDTH, HEIGHT), BACKGROUND)
    draw = ImageDraw.Draw(image)
    heights = len(lines) * (LINE_HEIGHT + 8)
    y = (HEIGHT - heights) // 2
    for index, line in enumerate(lines):
        font = bold if index == 0 else regular
        colour = FOREGROUND if index == 0 else (DIM if index >= len(lines) - 1 else FOREGROUND)
        width = draw.textlength(line, font=font)
        draw.text(((WIDTH - width) / 2, y), line, font=font, fill=colour)
        y += LINE_HEIGHT + 8
    return image


# ------------------------------------------------------------------ timeline

def beat_windows() -> dict[int, tuple[float, float]]:
    """Beat start and end, from the measured narration rather than from a plan."""
    if not TIMINGS.exists():
        raise RenderError(f"{TIMINGS.name} is missing. Run scripts/video_narration.py first.")
    windows: dict[int, tuple[float, float]] = {}
    for line in TIMINGS.read_text(encoding="utf-8").splitlines():
        if line.startswith("#") or not line.strip():
            continue
        start, end, beat, _ = line.split("\t", 3)
        number = int(beat)
        first, last = windows.get(number, (float(start), float(end)))
        windows[number] = (min(first, float(start)), max(last, float(end)))
    return windows


def prompt_line(typed: str):
    return [("$ ", PROMPT, True), (typed, FOREGROUND, False)]


def build_states(windows, fonts):
    """(seconds, image) key-frames for the whole video. Distinct screens are cached."""
    cache: dict = {}
    states = []

    def emit(at, key, make):
        if key not in cache:
            cache[key] = make()
        states.append((at, cache[key]))

    last_output = None
    for number in sorted(windows):
        start, end = windows[number]
        if number == 1:
            emit(start, ("card", "title"), lambda: card(TITLE, fonts))
            emit(end - 2.6, ("screen", ("",), None, None),
                 lambda: screen([prompt_line("")], (0, 2), None, fonts))
            continue

        kind, argv, typed = BEATS[number]
        if kind == "hold":
            if last_output is None:
                raise RenderError("beat 3 holds the previous output but there is none")
            lines, table = last_output
            emit(start, ("hold", number), lambda l=lines, t=table:
                 screen(l, None, t, fonts))
            continue

        wait, raw = capture(argv)
        body = to_lines(raw)
        cursor_row = 0
        for index in range(len(typed) + 1):
            at = start + index / TYPING_CPS
            if at >= end:
                break
            emit(at, ("type", number, index), lambda n=index:
                 screen([prompt_line(typed[:n])], (cursor_row, 2 + n), None, fonts))
        typed_at = start + len(typed) / TYPING_CPS
        emit(typed_at, ("wait", number), lambda:
             screen([prompt_line(typed), []], (1, 0), None, fonts))
        full = [prompt_line(typed), []] + body
        emit(typed_at + wait, ("out", number), lambda f=full: screen(f, None, None, fonts))
        if number == 2:
            head = next((i for i, row in enumerate(full)
                         if any("Based on" in text for text, _, _ in row)), None)
            last_output = (full, (head, len(full) - 1) if head is not None else None)

    end_of_narration = max(end for _, end in windows.values()) + GAP_BETWEEN_BEATS
    emit(end_of_narration, ("card", "closing"), lambda: card(CLOSING, fonts))
    states.append((end_of_narration + CLOSING_SECONDS, None))
    return states


def encode(states, probe_only: bool) -> int:
    import imageio_ffmpeg
    import numpy as np

    total = states[-1][0]
    print(f"video timeline {total:.2f} s ({int(total // 60)}:{int(total % 60):02d}), "
          f"{len(states) - 1} key frames")
    if probe_only:
        return 0

    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    silent = OUT.with_suffix(".silent.mp4")
    process = subprocess.Popen(
        [ffmpeg, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
         "-s", f"{WIDTH}x{HEIGHT}", "-r", str(FPS), "-i", "-",
         "-c:v", "libx264", "-preset", "medium", "-crf", "20",
         "-pix_fmt", "yuv420p", str(silent)], stdin=subprocess.PIPE)
    index, frames = 0, int(round(total * FPS))
    for frame in range(frames):
        at = frame / FPS
        while index + 1 < len(states) and states[index + 1][0] <= at:
            index += 1
        image = states[index][1]
        if image is None:
            break
        process.stdin.write(np.asarray(image, dtype=np.uint8).tobytes())
    process.stdin.close()
    if process.wait() != 0:
        raise RenderError("ffmpeg failed to encode the video track")

    muxed = subprocess.run(
        [ffmpeg, "-y", "-loglevel", "error", "-i", str(silent), "-i", str(NARRATION),
         "-i", str(CAPTIONS), "-map", "0:v", "-map", "1:a", "-map", "2",
         "-c:v", "copy", "-c:a", "aac", "-b:a", "128k", "-c:s", "mov_text",
         "-metadata:s:s:0", "language=eng", str(OUT)])
    # No -shortest here. The narration ends before the video does, on purpose: the closing
    # card is held in silence, and -shortest would trim the card off rather than pad the
    # audio.
    silent.unlink(missing_ok=True)
    if muxed.returncode != 0:
        raise RenderError("ffmpeg failed to mux narration and captions")
    print(f"wrote {OUT.relative_to(REPO)} ({OUT.stat().st_size / 1_000_000:.1f} MB)")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Render the submission video.")
    parser.add_argument("--probe", action="store_true",
                        help="capture the real runs and print their timings, encode nothing")
    args = parser.parse_args()
    try:
        if not NARRATION.exists():
            raise RenderError(f"{NARRATION.name} is missing. "
                              f"Run scripts/video_narration.py first.")
        fonts = load_fonts()
        windows = beat_windows()
        states = build_states(windows, fonts)
        return encode(states, args.probe)
    except RenderError as problem:
        print(f"error: {problem}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
