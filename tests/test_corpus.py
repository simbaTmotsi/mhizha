"""Corpus schema enforcement and chunking behaviour.

The schema tests exist because a chunk without provenance is a chunk we cannot defend,
and the failure has to happen at ingestion rather than at answer time.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from mhizha.corpus.chunk import chunk_document
from mhizha.corpus.clean import clean, is_table_line, repair_hyphenation
from mhizha.corpus.ingest import ingest_file, split_front_matter
from mhizha.corpus.review import ReviewLedger
from mhizha.corpus.schema import Chunk, Document
from mhizha.errors import SchemaError

VALID_FRONT = """---
source: "FIXTURE: doc"
publisher: "Test"
refresh_date: "2026-01-15"
lang: en
---

Some body text that is long enough to survive cleaning and chunking without trouble.
"""


def _write(tmp_path: Path, name: str, body: str) -> Path:
    path = tmp_path / name
    path.write_text(body, encoding="utf-8")
    return path


# ---------------------------------------------------------------- required fields


@pytest.mark.parametrize("missing", ["source", "publisher", "refresh_date", "lang"])
def test_ingest_fails_without_required_field(tmp_path: Path, missing: str) -> None:
    lines = [ln for ln in VALID_FRONT.splitlines() if not ln.startswith(f"{missing}:")]
    path = _write(tmp_path, "doc.md", "\n".join(lines))
    with pytest.raises(SchemaError) as exc:
        ingest_file(path)
    assert missing in str(exc.value)


def test_refresh_date_must_be_iso(tmp_path: Path) -> None:
    body = VALID_FRONT.replace('"2026-01-15"', '"January 2026"')
    path = _write(tmp_path, "doc.md", body)
    with pytest.raises(SchemaError, match="ISO"):
        ingest_file(path)


def test_refresh_date_is_never_defaulted_from_mtime(tmp_path: Path) -> None:
    """An undated planting calendar must be quarantined, never stamped with today."""
    lines = [ln for ln in VALID_FRONT.splitlines() if not ln.startswith("refresh_date:")]
    path = _write(tmp_path, "doc.md", "\n".join(lines))
    with pytest.raises(SchemaError):
        ingest_file(path)


def test_unknown_lang_rejected(tmp_path: Path) -> None:
    path = _write(tmp_path, "doc.md", VALID_FRONT.replace("lang: en", "lang: fr"))
    with pytest.raises(SchemaError, match="lang"):
        ingest_file(path)


def test_ingest_captures_provenance(tmp_path: Path) -> None:
    path = _write(tmp_path, "doc.md", VALID_FRONT)
    doc = ingest_file(path)
    assert doc.sha256 and len(doc.sha256) == 64
    assert doc.source_path == str(path)
    assert doc.ingested_at
    # Validation is granted by a human in the ledger, never by a file flag.
    assert doc.validated is False


def test_file_flag_cannot_grant_validation(tmp_path: Path) -> None:
    body = VALID_FRONT.replace("lang: en", "lang: en\nvalidated: true")
    path = _write(tmp_path, "doc.md", body)
    assert ingest_file(path).validated is False


def test_soft_warning_for_unknown_region(tmp_path: Path) -> None:
    body = VALID_FRONT.replace("lang: en", "lang: en\nregion: mashonalnd-central")
    doc = ingest_file(_write(tmp_path, "doc.md", body))
    assert any("region" in w for w in doc.soft_warnings())


# ---------------------------------------------------------------- chunk contract


def test_chunk_without_source_is_a_bug(fixture_config) -> None:
    chunk = Chunk(
        chunk_id="c1", doc_id="d1", text="text", ordinal=0, char_start=0, char_end=4,
        anchor="a", source="", publisher="p", refresh_date="2026-01-15", lang="en",
        crop="maize", region="national", season="summer", topic="general",
        placeholder=True, validated=False,
    )
    with pytest.raises(SchemaError, match="source or refresh_date"):
        chunk.validate()


def test_chunks_inherit_all_document_metadata(fixture_config) -> None:
    path = next(fixture_config.corpus.dir.glob("fixture-planting.md"))
    doc = ingest_file(path)
    chunks = chunk_document(doc, fixture_config.corpus.chunk)
    assert chunks
    for chunk in chunks:
        assert chunk.source == doc.source
        assert chunk.refresh_date == doc.refresh_date
        assert chunk.crop == doc.crop
        assert chunk.region == doc.region
        assert chunk.placeholder == doc.placeholder


def test_table_row_stays_with_its_header(tmp_path: Path, fixture_config) -> None:
    """A rate separated from its header column becomes a different instruction."""
    rows = "\n".join(
        f"| Row {i} | value | value | value |" for i in range(40)
    )
    body = (
        VALID_FRONT.rsplit("Some body", 1)[0]
        + "\n# Table\n\n| Crop | Product | Rate | Timing |\n| --- | --- | --- | --- |\n"
        + rows
        + "\n"
    )
    doc = ingest_file(_write(tmp_path, "table.md", body))
    chunks = chunk_document(doc, fixture_config.corpus.chunk)
    table_chunks = [c for c in chunks if "| Row 0 |" in c.text]
    assert table_chunks, "table content disappeared during chunking"
    assert "| Crop | Product | Rate | Timing |" in table_chunks[0].text


def test_chunk_ids_are_stable_and_ordered(fixture_config, fixture_chunks) -> None:
    ids = [c.chunk_id for c in fixture_chunks]
    assert len(ids) == len(set(ids))
    for chunk in fixture_chunks:
        assert chunk.chunk_id.startswith(chunk.doc_id)


# ---------------------------------------------------------------- cleaning


def test_hyphenation_repaired_across_line_breaks() -> None:
    assert "fertiliser" in repair_hyphenation("apply fertil-\niser now")


def test_page_furniture_stripped() -> None:
    pages = []
    for i in range(4):
        pages += ["AGRITEX HANDBOOK 2024", f"Content unique to page {i} goes here.", str(i)]
    cleaned = clean("\n".join(pages))
    assert "Content unique to page 2 goes here." in cleaned
    assert "AGRITEX HANDBOOK 2024" not in cleaned


def test_repeated_full_sentence_is_not_treated_as_furniture() -> None:
    """A genuine instruction can legitimately repeat across sections."""
    sentence = "Always read the product label before use."
    text = "\n".join([sentence, "AGRITEX HANDBOOK 2024"] * 4)
    cleaned = clean(text)
    assert sentence in cleaned
    assert "AGRITEX HANDBOOK 2024" not in cleaned


def test_table_lines_survive_furniture_stripping() -> None:
    table = "| Crop | Rate |"
    text = "\n".join([table, "body text here"] * 5)
    assert table in clean(text)


def test_is_table_line() -> None:
    assert is_table_line("| Crop | Rate |")
    assert not is_table_line("Plant when the rains have started.")


# ---------------------------------------------------------------- review ledger


def test_sign_off_requires_a_named_reviewer(tmp_path: Path, fixture_chunks) -> None:
    ledger = ReviewLedger(tmp_path / "ledger.jsonl")
    with pytest.raises(ValueError, match="reviewer"):
        ledger.sign(fixture_chunks[0], "   ")


def test_validated_only_after_sign_off(tmp_path: Path, fixture_chunks) -> None:
    ledger = ReviewLedger(tmp_path / "ledger.jsonl")
    chunk = fixture_chunks[0]
    assert ledger.status(chunk) == "unreviewed"
    ledger.sign(chunk, "A Reviewer")
    assert ledger.status(chunk) == "approved"
    chunks, counts = ledger.apply([chunk])
    assert chunks[0].validated is True
    assert counts["approved"] == 1


def test_changed_text_invalidates_prior_sign_off(tmp_path: Path, fixture_chunks) -> None:
    """A review of old text says nothing about new text."""
    ledger = ReviewLedger(tmp_path / "ledger.jsonl")
    chunk = fixture_chunks[0]
    ledger.sign(chunk, "A Reviewer")
    chunk.text = chunk.text + " An edit that changes the meaning."
    chunk.text_sha256 = ""
    chunk.__post_init__()
    assert ledger.status(chunk) == "stale"
    chunks, _ = ledger.apply([chunk])
    assert chunks[0].validated is False


def test_front_matter_parsing() -> None:
    meta, body = split_front_matter(VALID_FRONT)
    assert meta["publisher"] == "Test"
    assert "Some body text" in body


# ---------------------------------------------------------------- shipped corpus


def test_shipped_corpus_is_all_placeholder(repo_root: Path) -> None:
    """Nothing in data/corpus/ may claim to be real content while gaps are open."""
    corpus = repo_root / "data" / "corpus"
    docs = list(corpus.glob("*.md"))
    assert docs, "no documents in data/corpus/"
    for path in docs:
        doc = ingest_file(path)
        assert doc.placeholder is True, (
            f"{path.name} is not flagged placeholder: true. If it is real sourced "
            "content, remove the flag deliberately and record it in data/SOURCES.md."
        )
