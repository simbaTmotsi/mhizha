#!/usr/bin/env python3
"""BUILD TIME. Capture real CLI transcripts as submission assets.

WHY A SCRIPT RATHER THAN PASTED TERMINAL OUTPUT
-----------------------------------------------
A screenshot is a claim about what the software does, and a pasted one cannot be checked.
These are produced by running the CLI, so a reviewer can re-run this script and diff. If
the behaviour changes, the assets change with it, and a stale claim about our own product
cannot survive in the submission the way a pasted image would.

Every capture runs the shipped entry point with no special flags, against the placeholder
corpus that is actually in the repository. Nothing here is staged: the abstention is a real
abstention, and the placeholder banners appear because the corpus really is placeholder.

Writes docs/screenshots/<name>.txt and <name>.svg. The SVG is a plain monospace rendering
of the same text, for a submission page that wants an image rather than a code block.

Usage:
    python3 scripts/capture_cli.py            # all captures
    python3 scripts/capture_cli.py --list
"""
from __future__ import annotations

import argparse
import html
import os
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "docs" / "screenshots"

# Fixed width so a capture is stable across terminals and diffs cleanly.
COLUMNS = 88

CAPTURES = [
    {
        "name": "01-grounded-answer",
        "title": "A grounded answer, with its sources and confidence",
        "why": (
            "Every claim carries a passage id, and every passage names its source, "
            "publisher and refresh date. The placeholder banner is real: this corpus "
            "holds no agronomic content, and the system says so rather than sounding "
            "authoritative."
        ),
        "argv": ["ask", "when should I plant maize in Mashonaland"],
    },
    {
        "name": "02-abstention",
        "title": "Abstention: below the confidence threshold, the model is not called",
        "why": (
            "An out-of-corpus question. Mhizha says what it does not know, asks the one "
            "clarifying question that would unblock it, and refers the farmer to their "
            "local AGRITEX extension officer. The retrieved passages are still shown, "
            "with their low scores, so the decision is inspectable."
        ),
        "argv": ["ask", "how do I prune my avocado trees in winter"],
    },
    {
        "name": "03-agrochemical-safety",
        "title": "An agrochemical question: no rate is emitted, and the notice fires",
        "why": (
            "A dosage that is not verbatim in a validated passage is never emitted, in "
            "any phrasing. No validated passage exists here, so no rate appears, and the "
            "locale's chemical safety notice is attached with the referral to an "
            "extension officer."
        ),
        "argv": ["ask", "how much cypermethrin per litre of water for fall armyworm on maize"],
    },
    {
        "name": "04-doctor",
        "title": "make doctor: the device budget, accounted component by component",
        "why": (
            "The 4 GB phone profile is the default and stays the default. Every runtime "
            "component is costed against the headroom an app actually gets before the "
            "low-memory killer intervenes."
        ),
        "argv": ["doctor"],
    },
]

# The embedder's loader writes progress bars; they are terminal noise, not output.
NOISE = re.compile(r"^(Loading weights|Batches:|\s*$\r)", re.MULTILINE)


def run(argv: list[str]) -> str:
    env = dict(os.environ,
               PYTHONPATH=str(REPO / "src"),
               COLUMNS=str(COLUMNS),
               TERM="dumb")
    proc = subprocess.run([sys.executable, "-m", "mhizha", *argv],
                          cwd=REPO, env=env, capture_output=True, text=True)
    if proc.returncode != 0:
        raise SystemExit(f"capture failed: mhizha {' '.join(argv)}\n{proc.stderr[-2000:]}")
    lines = [ln for ln in (proc.stdout + proc.stderr).splitlines()
             if not NOISE.match(ln) and "it/s]" not in ln]
    text = "\n".join(lines).rstrip() + "\n"
    # `doctor` prints absolute config, index and embedder paths. These captures ship with
    # the submission, so the developer's home directory is replaced by a repo-relative
    # path, which is also what a reader running this from their own clone would see.
    # Same rule as scripts/scrub_runs.py, applied at the point the asset is made.
    return text.replace(str(REPO).rstrip("/") + "/", "")


def to_svg(text: str, title: str) -> str:
    """A monospace terminal rendering. No external fonts, no scripts, no colour tricks."""
    lines = text.splitlines() or [""]
    char_w, line_h, pad = 8.2, 17, 18
    width = int(max(COLUMNS, max(len(ln) for ln in lines)) * char_w + pad * 2)
    height = int(len(lines) * line_h + pad * 2 + 26)
    rows = []
    for index, line in enumerate(lines):
        y = pad + 26 + index * line_h
        rows.append(f'<text x="{pad}" y="{y}">{html.escape(line)}</text>')
    body = "\n    ".join(rows)
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}"
     viewBox="0 0 {width} {height}" role="img" aria-label="{html.escape(title)}">
  <rect width="100%" height="100%" rx="8" fill="#14161a"/>
  <circle cx="20" cy="18" r="5" fill="#3d4149"/>
  <circle cx="38" cy="18" r="5" fill="#3d4149"/>
  <circle cx="56" cy="18" r="5" fill="#3d4149"/>
  <text x="76" y="22" font-family="ui-monospace,SFMono-Regular,Menlo,monospace"
        font-size="11" fill="#8b919b">{html.escape(title)}</text>
  <g font-family="ui-monospace,SFMono-Regular,Menlo,Consolas,monospace"
     font-size="12.5" fill="#d7dae0" xml:space="preserve">
    {body}
  </g>
</svg>
'''


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true")
    args = ap.parse_args()

    if args.list:
        for capture in CAPTURES:
            print(f"{capture['name']:26s} mhizha {' '.join(capture['argv'])}")
        return 0

    OUT.mkdir(parents=True, exist_ok=True)
    for capture in CAPTURES:
        text = run(capture["argv"])
        (OUT / f"{capture['name']}.txt").write_text(text, encoding="utf-8")
        (OUT / f"{capture['name']}.svg").write_text(
            to_svg(text, capture["title"]), encoding="utf-8")
        print(f"  {capture['name']}: {len(text.splitlines())} lines")

    index = ["# CLI captures\n",
             "Produced by `python3 scripts/capture_cli.py`, which runs the shipped entry",
             "point against the placeholder corpus in this repository. Re-run it to check",
             "these are current; nothing here is staged or hand-edited.\n"]
    for capture in CAPTURES:
        index += [f"## {capture['title']}\n",
                  f"`mhizha {' '.join(capture['argv'])}`\n",
                  f"{capture['why']}\n",
                  f"![{capture['title']}](screenshots/{capture['name']}.svg)\n",
                  "<details><summary>as text</summary>\n",
                  "```",
                  (OUT / f"{capture['name']}.txt").read_text(encoding="utf-8").rstrip(),
                  "```\n", "</details>\n"]
    (REPO / "docs" / "SCREENSHOTS.md").write_text("\n".join(index), encoding="utf-8")
    print(f"\nwrote {OUT} and docs/SCREENSHOTS.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
