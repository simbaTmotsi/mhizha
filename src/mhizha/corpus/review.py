"""BUILD TIME. Human validation ledger.

A chunk is `validated` only when a named human has signed it off against its exact text
hash. Sign-off is recorded here, never set by a flag in a source file, because the point
of validation is that a person took responsibility for the words a farmer will read.

Re-ingesting a source changes chunk text hashes, which silently invalidates prior
sign-off. That is the intended behaviour: a review of old text says nothing about new
text.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path

from .schema import Chunk


@dataclass(frozen=True)
class ReviewRecord:
    chunk_id: str
    text_sha256: str
    reviewer: str
    reviewed_on: str
    verdict: str  # approved | rejected
    note: str = ""


class ReviewLedger:
    """Append-only JSONL ledger. Append-only so a sign-off history is auditable."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._records: list[ReviewRecord] | None = None

    def _load(self) -> list[ReviewRecord]:
        if self._records is not None:
            return self._records
        records: list[ReviewRecord] = []
        if self.path.exists():
            for line in self.path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                records.append(ReviewRecord(**json.loads(line)))
        self._records = records
        return records

    def sign(
        self,
        chunk: Chunk,
        reviewer: str,
        *,
        verdict: str = "approved",
        note: str = "",
        on: str | None = None,
    ) -> ReviewRecord:
        if verdict not in ("approved", "rejected"):
            raise ValueError("verdict must be 'approved' or 'rejected'")
        if not reviewer.strip():
            raise ValueError("reviewer name is required. Anonymous sign-off is not sign-off.")
        record = ReviewRecord(
            chunk_id=chunk.chunk_id,
            text_sha256=chunk.text_sha256,
            reviewer=reviewer.strip(),
            reviewed_on=on or date.today().isoformat(),
            verdict=verdict,
            note=note,
        )
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(asdict(record), ensure_ascii=False) + "\n")
        if self._records is not None:
            self._records.append(record)
        return record

    def status(self, chunk: Chunk) -> str:
        """approved | rejected | stale | unreviewed.

        `stale` means this chunk id was reviewed but the text has since changed.
        """
        latest_for_id: ReviewRecord | None = None
        for record in self._load():
            if record.chunk_id == chunk.chunk_id:
                latest_for_id = record
        if latest_for_id is None:
            return "unreviewed"
        if latest_for_id.text_sha256 != chunk.text_sha256:
            return "stale"
        return latest_for_id.verdict

    def apply(self, chunks: list[Chunk]) -> tuple[list[Chunk], dict[str, int]]:
        """Set `validated` on each chunk from the ledger. Returns (chunks, counts)."""
        counts = {"approved": 0, "rejected": 0, "stale": 0, "unreviewed": 0}
        for chunk in chunks:
            state = self.status(chunk)
            counts[state] += 1
            chunk.validated = state == "approved"
        return chunks, counts
