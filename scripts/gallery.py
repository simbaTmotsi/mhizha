#!/usr/bin/env python3
"""Render the Devpost image gallery, 3:2, from material already in this repository.

BUILD TIME. No network.

WHY THIS IS GENERATED
---------------------
A gallery is the part of a submission most likely to drift from the thing it shows: a
screenshot taken once, kept for weeks, and captioned from memory. Every image here is drawn
from a file the repository already holds -- the captured terminal sessions, the committed
captures, the superseded registry, the blind score sheet -- so a stale image is a rebuild
away rather than a re-shoot away.

Each image also refuses to be written if it contains an absolute home path. `doctor` prints
one, the committed capture has it relativised, and the difference between those two is
exactly the sort of thing that ends up published by accident.

Usage:
    python3 scripts/gallery.py
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))

import video_render as vr  # noqa: E402

OUT = REPO / "docs" / "gallery"
WIDTH, HEIGHT = 2400, 1600          # 3:2, the ratio Devpost asks for
MARGIN_X, MARGIN_Y = 110, 80
FONT = "/System/Library/Fonts/Menlo.ttc"

BG = vr.BACKGROUND
FG = vr.FOREGROUND
DIM = vr.DIM
ACCENT = vr.YELLOW


class GalleryError(RuntimeError):
    """Raised when an image would publish something it should not."""


def check(text: str, name: str) -> None:
    """No absolute home path reaches an image that is going onto the internet."""
    for probe in (str(REPO), "/Users/", "/home/"):
        if probe in text:
            raise GalleryError(
                f"{name} contains {probe!r}. Use the relativised capture, or relativise "
                f"the source, rather than publishing a developer's home directory.")


def fit(lines: list[str]) -> tuple[int, int]:
    """Largest legible type that fits both the widest line and the line count."""
    widest = max((len(line) for line in lines), default=1)
    by_width = (WIDTH - 2 * MARGIN_X) / (widest * 0.6015)
    by_height = (HEIGHT - 2 * MARGIN_Y) / (len(lines) * 1.25)
    size = int(min(by_width, by_height, 46))
    return max(size, 12), int(size * 1.25)


def draw(styled, name: str, accent_rows: set[int] | None = None):
    """One 3:2 image from styled terminal lines."""
    from PIL import Image, ImageDraw, ImageFont

    plain = ["".join(text for text, _, _ in row) for row in styled]
    check("\n".join(plain), name)
    size, leading = fit(plain)
    regular = ImageFont.truetype(FONT, size, index=0)
    bold = ImageFont.truetype(FONT, size, index=1)

    image = Image.new("RGB", (WIDTH, HEIGHT), BG)
    pen = ImageDraw.Draw(image)
    advance = pen.textlength("M", font=regular)
    block = len(plain) * leading
    top = max(MARGIN_Y, (HEIGHT - block) // 2)
    for index, row in enumerate(styled):
        x, y = MARGIN_X, top + index * leading
        for text, colour, is_bold in row:
            if accent_rows and index in accent_rows:
                colour = ACCENT
            pen.text((x, y), text, font=bold if is_bold else regular, fill=colour)
            x += advance * len(text)
    return image


def card(title: str, lines: list[tuple[str, bool]], footnote: str | None, name: str):
    """A titled card. `lines` is (text, emphasised)."""
    from PIL import Image, ImageDraw, ImageFont

    check(title + "\n".join(t for t, _ in lines) + (footnote or ""), name)
    display = ImageFont.truetype(FONT, 88, index=1)
    body = ImageFont.truetype(FONT, 38, index=0)
    strong = ImageFont.truetype(FONT, 38, index=1)
    small = ImageFont.truetype(FONT, 30, index=0)

    image = Image.new("RGB", (WIDTH, HEIGHT), BG)
    pen = ImageDraw.Draw(image)
    block = 88 + 46 + len(lines) * 58 + (78 if footnote else 0)
    y = (HEIGHT - block) // 2

    pen.text(((WIDTH - pen.textlength(title, font=display)) / 2, y), title,
             font=display, fill=FG)
    y += 88 + 22
    pen.line([(WIDTH - 190) / 2, y, (WIDTH + 190) / 2, y], fill=DIM, width=2)
    y += 30

    for text, emphasised in lines:
        font = strong if emphasised else body
        pen.text(((WIDTH - pen.textlength(text, font=font)) / 2, y), text,
                 font=font, fill=ACCENT if emphasised else FG)
        y += 58
    if footnote:
        y += 24
        pen.text(((WIDTH - pen.textlength(footnote, font=small)) / 2, y), footnote,
                 font=small, fill=DIM)
    return image


def styled(text: str):
    return vr.to_lines(text)


def rewrap(text: str, width: int = 104) -> list[str]:
    """Wrap long output with a hanging indent instead of at column zero.

    A terminal wraps to column zero because it has nowhere else to go. An image does, and a
    continuation line starting hard left reads as a rendering fault to anyone who does not
    know they are looking at a terminal. The text is unchanged; only where it breaks is.
    """
    rows: list[str] = []
    for line in text.split("\n"):
        indent = " " * (len(line) - len(line.lstrip(" ")))
        hang = indent + "  "
        current, prefix = "", indent
        for word in line.split():
            candidate = f"{current} {word}".strip()
            if current and len(prefix) + len(candidate) > width:
                rows.append(prefix + current)
                current, prefix = word, hang
            else:
                current = candidate
        rows.append(prefix + current if current else line)
    return rows


def plain_lines(text: str, colour=FG, bold=False):
    return [[(line, colour, bold)] for line in text.split("\n")]


def run(argv: list[str]) -> str:
    done = subprocess.run(argv, cwd=REPO, capture_output=True, text=True)
    return done.stdout + done.stderr


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    sessions = vr.load_sessions()
    images = []

    images.append(("01-mhizha", card(
        "Mhizha",
        [("An offline agronomy assistant for", False),
         ("smallholder farmers in Zimbabwe.", False),
         ("", False),
         ("It cites what it used, and refuses what it cannot source.", True)],
        "ADTC 2026  .  Laptop LLM track  .  domain: agriculture", "01")))

    images.append(("02-cited-answer", draw(
        [[("$ mhizha ask when should I plant maize in Mashonaland", vr.PROMPT, True)], []]
        + styled(sessions[2][1]), "02")))

    images.append(("03-refuses-a-dose", draw(
        [[("$ mhizha ask how much cypermethrin per litre of water for fall armyworm",
           vr.PROMPT, True)], []]
        + styled(sessions[4][1]), "03")))

    images.append(("04-abstains", draw(
        [[("$ mhizha ask how do I prune my avocado trees in winter", vr.PROMPT, True)], []]
        + styled(sessions[5][1]), "04")))

    images.append(("05-what-is-profiled", draw(
        [[("$ cat competition/system_prompt.txt", vr.PROMPT, True)], []]
        + styled(sessions[6][1]), "05")))

    figures = run([vr.PY, "scripts/report_figures.py"])
    images.append(("06-untraceable-numbers-fail-the-build", draw(
        [[("$ python3 scripts/report_figures.py", vr.PROMPT, True)], []]
        + plain_lines("\n".join(rewrap(figures))), "06")))

    doctor = (REPO / "docs" / "screenshots" / "04-doctor.txt").read_text(encoding="utf-8")
    images.append(("07-fits-a-4gb-phone", draw(plain_lines(doctor), "07")))

    images.append(("08-chosen-blind", card(
        "Chosen blind",
        [("arm    grounded  refusal  concise  relevance   total", False),
         ("", False),
         ("C           30       10       27         28      95", True),
         ("B           28       10       27         28      93", False),
         ("A           25        8       21         27      81", False),
         ("", False),
         ("The mapping was sealed before a single score existed.", False),
         ("C was the 2B. The accuracy proxy favoured the 4B by twelve points.", False)],
        "runs/20260820T105919Z_blind/SCORES.md", "08")))

    images.append(("09-what-we-got-wrong", card(
        "13 reversed conclusions",
        [("Each one recorded with the evidence that overturned it,", False),
         ("and the build fails if a retracted claim reappears.", False),
         ("", False),
         ("SR-01  submit the conservative figure   would have failed the audit", False),
         ("SR-09  steal screening is sufficient    67.9% spread at zero steal", False),
         ("SR-12  the sitting verifies the ranking there was no ranking to verify", False)],
        "competition/superseded.yaml", "09")))

    images.append(("10-no-number-by-hand", card(
        "Absence fails closed",
        [("A missing measurement is Absent, never zero.", True),
         ("", False),
         ("Latency is quotable only from a physical machine.", False),
         ("We never got one, so the report carries no latency figure at all", False),
         ("and says why. Telemetry fell back, and is labelled FALLBACK", False),
         ("with its measured spread printed beside it.", False)],
        "COMPETITION.md section 9g  .  scripts/run_guards.py", "10")))

    for name, image in images:
        target = OUT / f"{name}.png"
        image.save(target, optimize=True)
        size = target.stat().st_size / 1_000_000
        if size > 5:
            raise GalleryError(f"{name} is {size:.1f} MB, over the 5 MB gallery limit")
        print(f"  {target.relative_to(REPO)}  {WIDTH}x{HEIGHT}  {size:.2f} MB")
    print(f"\n{len(images)} images, 3:2, none containing an absolute path")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except GalleryError as problem:
        print(f"error: {problem}", file=sys.stderr)
        sys.exit(1)
