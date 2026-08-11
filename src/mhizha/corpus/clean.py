"""BUILD TIME. Text normalisation for ingested source documents.

Extension material arrives as scanned PDFs, printed booklets, and Word documents. The
cleaning here fixes the predictable damage that causes: hyphens broken across line ends,
repeated page furniture, and unicode variants of the same character.

Tables are preserved deliberately. Fertiliser rates and spray schedules are the highest
value content in this corpus and also the easiest to mangle into something dangerous.
"""

from __future__ import annotations

import re
import unicodedata
from collections import Counter

# A word split across a line break: "fertil-\niser" becomes "fertiliser".
_HYPHEN_BREAK = re.compile(r"(\w)-\s*\n\s*(\w)")
_MULTI_BLANK = re.compile(r"\n{3,}")
_TRAILING_WS = re.compile(r"[ \t]+$", re.MULTILINE)
_PAGE_NUMBER = re.compile(r"^\s*(?:page\s+)?\d{1,3}\s*(?:of\s+\d{1,3})?\s*$", re.IGNORECASE)
_TABLE_LINE = re.compile(r"\|.*\||\t.*\t|\s{3,}\S+\s{3,}\S+")


def normalise_unicode(text: str) -> str:
    """NFKC, then map the punctuation variants that break exact-match safety checks."""
    text = unicodedata.normalize("NFKC", text)
    replacements = {
        "‘": "'", "’": "'", "“": '"', "”": '"',
        "–": "-", "—": "-", "−": "-", " ": " ",
        "…": "...", "﻿": "",
    }
    for bad, good in replacements.items():
        text = text.replace(bad, good)
    return text


def repair_hyphenation(text: str) -> str:
    prev = None
    while prev != text:
        prev = text
        text = _HYPHEN_BREAK.sub(r"\1\2", text)
    return text


def is_table_line(line: str) -> bool:
    """Heuristic. Used to protect table blocks from reflowing and from chunk splits."""
    return bool(_TABLE_LINE.search(line))


def strip_page_furniture(text: str, min_repeats: int = 3) -> str:
    """Remove headers, footers, and page numbers.

    A line is furniture if it repeats at least `min_repeats` times, is short, is not
    part of a table, and does not read as a complete sentence. Repetition alone is not
    enough: a genuine instruction can legitimately repeat across sections, and stripping
    it would remove content while leaving the document looking intact.
    """
    lines = text.split("\n")
    counts = Counter(ln.strip() for ln in lines if ln.strip())
    furniture = {
        ln for ln, n in counts.items()
        if n >= min_repeats
        and len(ln) <= 80
        and not is_table_line(ln)
        and not ln.rstrip().endswith((".", "!", "?", ":"))
    }
    kept = [
        ln for ln in lines
        if ln.strip() not in furniture and not _PAGE_NUMBER.match(ln)
    ]
    return "\n".join(kept)


def clean(text: str, *, strip_furniture: bool = True) -> str:
    """Full cleaning pass. Order matters: unicode first, hyphens before furniture."""
    text = normalise_unicode(text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = repair_hyphenation(text)
    if strip_furniture:
        text = strip_page_furniture(text)
    text = _TRAILING_WS.sub("", text)
    text = _MULTI_BLANK.sub("\n\n", text)
    return text.strip()
