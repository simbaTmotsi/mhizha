"""BUILD TIME. Metadata-preserving chunker.

The rule that shapes this module: never separate a quantity from its qualifier. A spray
rate without its crop column, a dosage without its units, or an instruction without its
"only on soils with pH above" caveat is not merely a worse chunk. It is a chunk that can
produce a confident, cited, harmful answer.

So table blocks are kept whole with their header row, and splits prefer heading and
paragraph boundaries over hitting a character target exactly.
"""

from __future__ import annotations

import re

from ..config import ChunkConfig
from .clean import is_table_line
from .schema import Chunk, Document, make_chunk_id

_HEADING = re.compile(r"^\s{0,3}(#{1,6}\s+\S|[A-Z][A-Z0-9 \-/&()]{4,}\s*$)")
_LIST_ITEM = re.compile(r"^\s*(?:[-*+]\s+|\d{1,2}[.)]\s+)")


class _Block:
    """A run of lines that must not be split internally."""

    __slots__ = ("lines", "kind", "start", "end", "heading")

    def __init__(self, kind: str, start: int, heading: str = "") -> None:
        self.lines: list[str] = []
        self.kind = kind
        self.start = start
        self.end = start
        self.heading = heading

    @property
    def text(self) -> str:
        return "\n".join(self.lines).strip("\n")

    def __len__(self) -> int:
        return len(self.text)


def _segment(text: str, respect_tables: bool) -> list[_Block]:
    """Split into atomic blocks: table blocks, headings, paragraphs, list runs."""
    blocks: list[_Block] = []
    cursor = 0
    current: _Block | None = None
    heading = ""

    for line in text.split("\n"):
        line_start = cursor
        cursor += len(line) + 1
        stripped = line.strip()

        if not stripped:
            if current is not None:
                current.end = line_start
                blocks.append(current)
                current = None
            continue

        if _HEADING.match(line):
            if current is not None:
                current.end = line_start
                blocks.append(current)
            heading = stripped.lstrip("#").strip()
            current = _Block("heading", line_start, heading)
            current.lines.append(line)
            current.end = cursor
            blocks.append(current)
            current = None
            continue

        kind = "table" if (respect_tables and is_table_line(line)) else (
            "list" if _LIST_ITEM.match(line) else "para"
        )

        if current is None or (current.kind != kind and kind == "table") or (
            current.kind == "table" and kind != "table"
        ):
            if current is not None:
                current.end = line_start
                blocks.append(current)
            current = _Block(kind, line_start, heading)

        current.lines.append(line)
        current.end = cursor

    if current is not None:
        blocks.append(current)

    return [b for b in blocks if b.text.strip()]


def _overlap_tail(text: str, overlap_chars: int) -> str:
    """Take the tail of the previous chunk, snapped to a sentence boundary if possible.

    The overlap exists so a boundary never orphans a qualifier. Snapping to a sentence
    keeps the carried text readable to the model rather than starting mid-clause.
    """
    if overlap_chars <= 0 or len(text) <= overlap_chars:
        return text if overlap_chars > 0 else ""
    tail = text[-overlap_chars:]
    match = re.search(r"(?<=[.!?])\s+", tail)
    return tail[match.end():] if match else tail


def chunk_document(doc: Document, cfg: ChunkConfig) -> list[Chunk]:
    """Chunk a cleaned document, carrying every metadata field onto every chunk."""
    blocks = _segment(doc.text, cfg.respect_tables)
    if not blocks:
        return []

    chunks: list[Chunk] = []
    buf: list[_Block] = []
    buf_len = 0
    carry = ""

    def flush() -> None:
        nonlocal buf, buf_len, carry
        if not buf:
            return
        body = "\n\n".join(b.text for b in buf)
        text = f"{carry}\n\n{body}".strip() if carry else body
        heading = next((b.heading for b in buf if b.heading), "")
        anchor = heading or f"offset:{buf[0].start}"
        ordinal = len(chunks)
        chunks.append(
            Chunk(
                chunk_id=make_chunk_id(doc.doc_id, ordinal),
                doc_id=doc.doc_id,
                text=text,
                ordinal=ordinal,
                char_start=buf[0].start,
                char_end=buf[-1].end,
                anchor=anchor,
                source=doc.source,
                publisher=doc.publisher,
                refresh_date=doc.refresh_date,
                lang=doc.lang,
                crop=doc.crop,
                region=doc.region,
                season=doc.season,
                topic=doc.topic,
                placeholder=doc.placeholder,
                validated=doc.validated,
            )
        )
        carry = _overlap_tail(body, cfg.overlap_chars)
        buf = []
        buf_len = 0

    for block in blocks:
        blen = len(block)

        # A table block larger than max_chars is emitted whole anyway. An oversized
        # chunk is a performance cost. A split spray table is a safety cost.
        if block.kind == "table" and blen > cfg.max_chars:
            flush()
            buf = [block]
            buf_len = blen
            flush()
            continue

        # A heading belongs with what follows it, never trailing the previous chunk.
        if block.kind == "heading" and buf_len >= cfg.target_chars:
            flush()

        if buf_len + blen > cfg.max_chars and buf:
            flush()

        buf.append(block)
        buf_len += blen + 2

        if buf_len >= cfg.target_chars and block.kind not in ("heading", "table"):
            flush()

    flush()

    # A trailing heading-only chunk carries no content. Fold it back.
    if len(chunks) > 1 and len(chunks[-1].text) < 40:
        tail = chunks.pop()
        merged = chunks[-1]
        merged.text = f"{merged.text}\n\n{tail.text}"
        merged.char_end = tail.char_end
        merged.text_sha256 = ""
        merged.__post_init__()

    for c in chunks:
        c.validate()
    return chunks
