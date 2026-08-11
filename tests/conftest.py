"""Shared fixtures.

Test fixtures use invented products and invented crops. They are NOT agronomic content
and never enter data/corpus/. The one place a quantity appears verbatim is the fictional
"Fixture Product Z", which exists solely to exercise the allowed branch of the
agrochemical guard. It names no real product and no real crop.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from mhizha.config import load_config  # noqa: E402
from mhizha.corpus.chunk import chunk_document  # noqa: E402
from mhizha.corpus.ingest import ingest_file  # noqa: E402
from mhizha.rag.embedder import load_embedder  # noqa: E402
from mhizha.rag.index import build_index, open_index  # noqa: E402
from mhizha.rag.store import Hit  # noqa: E402

FIXTURE_DOCS = {
    "fixture-planting.md": """---
source: "FIXTURE: Planting window structure"
publisher: "Test fixture"
refresh_date: "2026-01-15"
lang: en
crop: maize
region: mashonaland-central
season: summer
topic: planting-calendar
placeholder: true
---

# Planting window structure

This fixture describes the planting window for maize in Mashonaland Central without
stating any date. The window is recorded once a validated source is available.

Planting decisions in this region follow the onset of effective rains rather than a fixed
calendar date.
""",
    "fixture-chemical.md": """---
source: "FIXTURE: Fictional product record"
publisher: "Test fixture"
refresh_date: "2026-01-15"
lang: en
crop: unspecified
region: national
season: all-year
topic: pest-management
placeholder: true
---

# Fictional product record

Fixture Product Z is an invented product that does not exist and is not registered
anywhere. In this fixture the spray rate for Fixture Product Z is recorded as 17 ml per
10 litres of water, purely so the agrochemical guard's verbatim-match branch can be
tested.

No real product, crop, or rate is described in this document.
""",
    "fixture-storage.md": """---
source: "FIXTURE: Storage structure"
publisher: "Test fixture"
refresh_date: "2026-01-15"
lang: en
crop: maize
region: national
season: post-harvest
topic: post-harvest
placeholder: true
---

# Storage structure

Grain storage guidance for maize is recorded here once sourced. This fixture states no
moisture content and no drying period.
""",
}


@pytest.fixture(scope="session")
def repo_root() -> Path:
    return REPO_ROOT


@pytest.fixture()
def fixture_config(tmp_path: Path):
    """A config pointing at an isolated corpus and index, using the hash embedder.

    The hash embedder keeps the suite fast and free of a model download. Retrieval
    quality is not what these tests measure: rules and plumbing are.
    """
    base = yaml.safe_load((REPO_ROOT / "config.yaml").read_text(encoding="utf-8"))
    corpus_dir = tmp_path / "corpus"
    corpus_dir.mkdir()
    for name, body in FIXTURE_DOCS.items():
        (corpus_dir / name).write_text(body, encoding="utf-8")

    base["corpus"]["dir"] = str(corpus_dir)
    base["corpus"]["raw_dir"] = str(tmp_path / "raw")
    base["corpus"]["review_ledger"] = str(tmp_path / "ledger.jsonl")
    base["index"]["path"] = str(tmp_path / "index" / "test.db")
    base["embedder"]["path"] = str(tmp_path / "no-weights-here")
    base["embedder"]["allow_hash_fallback"] = True

    cfg_path = tmp_path / "config.yaml"
    cfg_path.write_text(yaml.safe_dump(base), encoding="utf-8")
    return load_config(cfg_path)


@pytest.fixture()
def fixture_chunks(fixture_config):
    chunks = []
    for path in sorted(fixture_config.corpus.dir.glob("*.md")):
        doc = ingest_file(path)
        chunks.extend(chunk_document(doc, fixture_config.corpus.chunk))
    return chunks


@pytest.fixture()
def built_index(fixture_config, fixture_chunks):
    build_index(fixture_config, fixture_chunks)
    store = open_index(fixture_config)
    yield fixture_config, store
    store.close()


@pytest.fixture()
def embedder(fixture_config):
    return load_embedder(fixture_config.embedder)


def make_hit(
    text: str,
    *,
    chunk_id: str = "c1",
    score: float = 0.9,
    validated: bool = True,
    placeholder: bool = False,
    doc_id: str = "d1",
    crop: str = "maize",
) -> Hit:
    """Construct a Hit directly, for safety tests that need no index."""
    return Hit(
        chunk_id=chunk_id,
        text=text,
        score=score,
        source="FIXTURE: source",
        publisher="Test fixture",
        refresh_date="2026-01-15",
        crop=crop,
        region="national",
        season="all-year",
        topic="general",
        lang="en",
        anchor="section",
        doc_id=doc_id,
        placeholder=placeholder,
        validated=validated,
    )
