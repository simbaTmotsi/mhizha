"""BUILD TIME. Source document ingestion with provenance capture.

Network access is permitted in this module (build time only) but is not currently used:
sources arrive as files in data/raw/. If a fetch adapter is added, it logs the URL and
the retrieval date, because provenance not captured at ingest cannot be recovered later.

Required metadata (source, publisher, refresh_date, lang) comes from markdown front
matter or a sidecar <filename>.meta.yaml. It is never guessed from the filename and
never defaulted from the file mtime.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

import yaml

from ..errors import IngestError, SchemaError
from .clean import clean
from .schema import Document, make_doc_id

MARKDOWN_SUFFIXES = {".md", ".markdown"}
TEXT_SUFFIXES = {".txt"}
PDF_SUFFIXES = {".pdf"}
DOCX_SUFFIXES = {".docx"}

SUPPORTED = MARKDOWN_SUFFIXES | TEXT_SUFFIXES | PDF_SUFFIXES | DOCX_SUFFIXES


@dataclass
class IngestResult:
    documents: list[Document]
    quarantined: list[tuple[Path, str]]
    warnings: list[tuple[Path, str]]

    @property
    def ok(self) -> bool:
        return not self.quarantined


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def split_front_matter(text: str) -> tuple[dict, str]:
    """Parse leading `---` YAML front matter. Returns (metadata, body)."""
    if not text.lstrip().startswith("---"):
        return {}, text
    stripped = text.lstrip()
    parts = stripped.split("---", 2)
    if len(parts) < 3:
        return {}, text
    try:
        meta = yaml.safe_load(parts[1]) or {}
    except yaml.YAMLError as exc:
        raise IngestError(f"malformed front matter: {exc}") from exc
    if not isinstance(meta, dict):
        return {}, text
    return meta, parts[2]


def _sidecar_meta(path: Path) -> dict:
    for candidate in (
        path.with_suffix(path.suffix + ".meta.yaml"),
        path.with_suffix(".meta.yaml"),
    ):
        if candidate.exists():
            data = yaml.safe_load(candidate.read_text(encoding="utf-8")) or {}
            if not isinstance(data, dict):
                raise IngestError(f"{candidate}: sidecar metadata must be a mapping")
            return data
    return {}


# ---------------------------------------------------------------- format adapters


def _read_markdown(path: Path) -> tuple[str, dict]:
    meta, body = split_front_matter(path.read_text(encoding="utf-8"))
    return body, meta


def _read_text(path: Path) -> tuple[str, dict]:
    return path.read_text(encoding="utf-8"), {}


def _read_pdf(path: Path) -> tuple[str, dict]:
    try:
        from pypdf import PdfReader
    except ImportError as exc:  # pragma: no cover - environment dependent
        raise IngestError(
            f"{path.name}: PDF ingestion needs pypdf. Run `pip install pypdf` "
            "(build time only, never ships to the device)."
        ) from exc
    reader = PdfReader(str(path))
    pages: list[str] = []
    for i, page in enumerate(reader.pages, start=1):
        extracted = page.extract_text() or ""
        # The page anchor is the citation granularity an extension officer can check.
        pages.append(f"[page {i}]\n{extracted}")
    meta = {}
    info = getattr(reader, "metadata", None)
    if info and getattr(info, "title", None):
        meta["source"] = str(info.title)
    return "\n\n".join(pages), meta


def _read_docx(path: Path) -> tuple[str, dict]:
    try:
        import docx  # python-docx
    except ImportError as exc:  # pragma: no cover - environment dependent
        raise IngestError(
            f"{path.name}: DOCX ingestion needs python-docx. Run "
            "`pip install python-docx` (build time only, never ships to the device)."
        ) from exc
    document = docx.Document(str(path))
    parts: list[str] = [p.text for p in document.paragraphs if p.text.strip()]
    # Tables are rendered pipe-delimited so the chunker recognises and protects them.
    for table in document.tables:
        for row in table.rows:
            cells = [c.text.strip().replace("\n", " ") for c in row.cells]
            parts.append("| " + " | ".join(cells) + " |")
    return "\n\n".join(parts), {}


ADAPTERS: dict[str, Callable[[Path], tuple[str, dict]]] = {}
for suffix in MARKDOWN_SUFFIXES:
    ADAPTERS[suffix] = _read_markdown
for suffix in TEXT_SUFFIXES:
    ADAPTERS[suffix] = _read_text
for suffix in PDF_SUFFIXES:
    ADAPTERS[suffix] = _read_pdf
for suffix in DOCX_SUFFIXES:
    ADAPTERS[suffix] = _read_docx


# ---------------------------------------------------------------- ingestion


def ingest_file(path: Path, *, extra_meta: dict | None = None) -> Document:
    """Ingest one file into a validated Document. Raises on missing required metadata."""
    suffix = path.suffix.lower()
    adapter = ADAPTERS.get(suffix)
    if adapter is None:
        raise IngestError(
            f"{path.name}: unsupported format {suffix!r}. Supported: {sorted(SUPPORTED)}"
        )

    raw_text, embedded_meta = adapter(path)
    meta: dict = {}
    meta.update(embedded_meta)
    meta.update(_sidecar_meta(path))
    meta.update(extra_meta or {})

    text = clean(raw_text, strip_furniture=suffix in PDF_SUFFIXES | DOCX_SUFFIXES)
    if not text.strip():
        raise IngestError(
            f"{path.name}: no text after cleaning. If this is a scanned PDF it needs OCR. "
            "Do not hand-transcribe agronomic content into the corpus without sign-off."
        )

    sha = _sha256_file(path)
    doc = Document(
        doc_id=make_doc_id(str(path), sha),
        text=text,
        source=str(meta.get("source", "")),
        publisher=str(meta.get("publisher", "")),
        refresh_date=str(meta.get("refresh_date", "")),
        lang=str(meta.get("lang", "")),
        source_path=str(path),
        sha256=sha,
        ingested_at=_now(),
        crop=str(meta.get("crop", "unspecified")),
        region=str(meta.get("region", "national")),
        season=str(meta.get("season", "all-year")),
        topic=str(meta.get("topic", "general")),
        placeholder=bool(meta.get("placeholder", False)),
        # Validation is granted by a human in the review ledger, never by a file flag.
        validated=False,
        notes=str(meta.get("notes", "")),
    )
    doc.validate()
    return doc


def ingest_directory(directory: Path, *, recursive: bool = True) -> IngestResult:
    """Ingest every supported file under `directory`, quarantining failures."""
    documents: list[Document] = []
    quarantined: list[tuple[Path, str]] = []
    warnings: list[tuple[Path, str]] = []

    pattern = "**/*" if recursive else "*"
    for path in sorted(directory.glob(pattern)):
        if not path.is_file() or path.suffix.lower() not in SUPPORTED:
            continue
        if path.name.endswith(".meta.yaml"):
            continue
        try:
            doc = ingest_file(path)
        except (IngestError, SchemaError) as exc:
            quarantined.append((path, str(exc)))
            continue
        for warning in doc.soft_warnings():
            warnings.append((path, warning))
        documents.append(doc)

    return IngestResult(documents=documents, quarantined=quarantined, warnings=warnings)
