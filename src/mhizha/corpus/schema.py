"""BUILD TIME. The corpus contract.

`source` and `refresh_date` are required on every document and therefore on every chunk.
They are what make an answer defensible to a farmer and to an extension officer. A chunk
we cannot attribute is a chunk we cannot serve, so ingestion fails rather than defaults.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass, field
from datetime import date
from typing import Any

from ..errors import SchemaError

REQUIRED_DOC_FIELDS = ("source", "publisher", "refresh_date", "lang")

VALID_LANGS = ("en", "sn", "nd")

# Open vocabularies. Values outside them are allowed but reported, because a typo in a
# region name silently removes a passage from every filtered query.
KNOWN_REGIONS = (
    "national",
    "mashonaland-central",
    "mashonaland-east",
    "mashonaland-west",
    "manicaland",
    "masvingo",
    "matabeleland-north",
    "matabeleland-south",
    "midlands",
    "harare",
    "bulawayo",
)
KNOWN_SEASONS = ("summer", "winter", "all-year", "pre-season", "post-harvest")
KNOWN_TOPICS = (
    "crop-selection",
    "planting-calendar",
    "pest-management",
    "disease-management",
    "soil-fertility",
    "water-irrigation",
    "post-harvest",
    "general",
)

_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@dataclass
class Document:
    """A cleaned source document, before chunking."""

    doc_id: str
    text: str
    source: str
    publisher: str
    refresh_date: str
    lang: str
    source_path: str
    sha256: str
    ingested_at: str
    crop: str = "unspecified"
    region: str = "national"
    season: str = "all-year"
    topic: str = "general"
    placeholder: bool = False
    validated: bool = False
    notes: str = ""

    def validate(self) -> None:
        missing = [f for f in REQUIRED_DOC_FIELDS if not getattr(self, f, None)]
        if missing:
            raise SchemaError(
                f"{self.source_path}: missing required field(s): {', '.join(missing)}. "
                "Supply them in front matter or a sidecar .meta.yaml. They are never "
                "inferred from the filename or the file mtime."
            )
        if not _ISO_DATE.match(str(self.refresh_date)):
            raise SchemaError(
                f"{self.source_path}: refresh_date must be ISO YYYY-MM-DD, got "
                f"{self.refresh_date!r}. An undated planting calendar is a liability."
            )
        if self.lang not in VALID_LANGS:
            raise SchemaError(
                f"{self.source_path}: lang must be one of {VALID_LANGS}, got {self.lang!r}"
            )
        if not self.text.strip():
            raise SchemaError(f"{self.source_path}: document text is empty after cleaning")

    def soft_warnings(self) -> list[str]:
        """Non-fatal issues worth reporting. A typo here quietly hides a passage."""
        warnings: list[str] = []
        if self.region not in KNOWN_REGIONS:
            warnings.append(f"region {self.region!r} is not a known region value")
        if self.season not in KNOWN_SEASONS:
            warnings.append(f"season {self.season!r} is not a known season value")
        if self.topic not in KNOWN_TOPICS:
            warnings.append(f"topic {self.topic!r} is not a known topic value")
        try:
            if date.fromisoformat(self.refresh_date) > date.today():
                warnings.append("refresh_date is in the future")
        except ValueError:
            pass
        return warnings


@dataclass
class Chunk:
    """A retrievable unit. Carries the full provenance of its parent document."""

    chunk_id: str
    doc_id: str
    text: str
    ordinal: int
    char_start: int
    char_end: int
    anchor: str
    source: str
    publisher: str
    refresh_date: str
    lang: str
    crop: str
    region: str
    season: str
    topic: str
    placeholder: bool
    validated: bool
    text_sha256: str = ""
    embedding: list[float] | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        if not self.text_sha256:
            self.text_sha256 = _sha256(self.text)

    def validate(self) -> None:
        if not self.source or not self.refresh_date:
            raise SchemaError(
                f"chunk {self.chunk_id} lost source or refresh_date during chunking. "
                "This is a bug in the chunker, not a formatting quirk."
            )
        if not self.text.strip():
            raise SchemaError(f"chunk {self.chunk_id} is empty")

    def citation(self) -> str:
        """One-line human-readable attribution shown under an answer."""
        return f"{self.source} ({self.publisher}, refreshed {self.refresh_date})"

    def to_row(self) -> dict[str, Any]:
        d = asdict(self)
        d.pop("embedding", None)
        d["placeholder"] = int(self.placeholder)
        d["validated"] = int(self.validated)
        return d


def chunks_to_json(chunks: list[Chunk]) -> str:
    payload = []
    for c in chunks:
        d = asdict(c)
        d.pop("embedding", None)
        payload.append(d)
    return json.dumps(payload, indent=2, ensure_ascii=False)


def chunks_from_json(text: str) -> list[Chunk]:
    return [Chunk(**d) for d in json.loads(text)]


def make_doc_id(source_path: str, sha: str) -> str:
    stem = re.sub(r"[^a-z0-9]+", "-", source_path.lower().rsplit("/", 1)[-1]).strip("-")
    return f"{stem}-{sha[:8]}"


def make_chunk_id(doc_id: str, ordinal: int) -> str:
    return f"{doc_id}#{ordinal:04d}"
