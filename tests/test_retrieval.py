"""Retrieval rules and confidence scoring.

Every rule in rag/retrieve.py and rag/store.py has a case here, including the boundary
cases at the abstention threshold, because the threshold is where the safety behaviour
actually changes.
"""

from __future__ import annotations

import dataclasses

import numpy as np
import pytest

from mhizha.errors import EmbedderMismatchError, IndexError_
from mhizha.rag.index import build_index, open_index
from mhizha.rag.retrieve import detect_regions, retrieve, score_confidence
from mhizha.rag.store import Filters, VectorStore

from conftest import make_hit


# ---------------------------------------------------------------- index integrity


def test_index_records_embedder_identity(built_index) -> None:
    cfg, store = built_index
    assert store.get_meta("embedder_id")
    assert int(store.get_meta("embedder_dim")) == cfg.embedder.dim
    assert store.get_meta("corpus_sha256")


def test_embedder_mismatch_raises_loudly(built_index) -> None:
    """A silent mismatch produces confident nonsense, so it must be an error."""
    cfg, store = built_index
    store.set_meta("embedder_id", "some-other-embedder")
    with pytest.raises(EmbedderMismatchError, match="some-other-embedder"):
        open_index(cfg)


def test_dimension_mismatch_raises(built_index) -> None:
    cfg, store = built_index
    with pytest.raises(EmbedderMismatchError):
        store.search(np.zeros(cfg.embedder.dim + 3, dtype=np.float32), 3)


def test_missing_index_raises_actionable_error(fixture_config) -> None:
    with pytest.raises(IndexError_, match="developer machine"):
        open_index(fixture_config)


def test_build_fails_on_empty_corpus(fixture_config) -> None:
    with pytest.raises(IndexError_, match="no chunks"):
        build_index(fixture_config, [])


def test_index_is_a_single_file(built_index) -> None:
    """The single-file property is a shipping constraint, not an implementation detail."""
    cfg, store = built_index
    assert cfg.index.path.is_file()
    siblings = [p for p in cfg.index.path.parent.iterdir() if p.suffix not in
                (".db-wal", ".db-shm")]
    assert siblings == [cfg.index.path]


# ---------------------------------------------------------------- retrieval


def test_retrieval_returns_provenance_never_bare_text(built_index, embedder) -> None:
    cfg, store = built_index
    result = retrieve("planting window for maize", store, embedder, cfg)
    assert result.hits
    for hit in result.hits:
        assert hit.source and hit.publisher and hit.refresh_date
        assert hit.chunk_id


def test_results_are_ordered_by_score(built_index, embedder) -> None:
    cfg, store = built_index
    result = retrieve("maize planting", store, embedder, cfg)
    scores = [h.score for h in result.hits]
    assert scores == sorted(scores, reverse=True)


def test_top_k_is_respected(built_index, embedder) -> None:
    cfg, store = built_index
    result = retrieve("maize", store, embedder, cfg, top_k=2)
    assert len(result.hits) <= 2


def test_crop_filter_excludes_other_crops(built_index, embedder) -> None:
    cfg, store = built_index
    result = retrieve(
        "storage", store, embedder, cfg,
        filters=Filters(crop="maize", allow_placeholder=True),
    )
    assert all(h.crop == "maize" for h in result.hits)


def test_region_filter_keeps_national_content(built_index, embedder) -> None:
    """National guidance applies everywhere, so a region filter must not hide it."""
    cfg, store = built_index
    result = retrieve(
        "storage guidance", store, embedder, cfg,
        filters=Filters(region="mashonaland-central", allow_placeholder=True),
    )
    regions = {h.region for h in result.hits}
    assert regions <= {"mashonaland-central", "national"}
    assert "national" in regions


def test_validated_only_filter_is_queryable_without_rebuild(built_index, embedder) -> None:
    cfg, store = built_index
    result = retrieve(
        "maize", store, embedder, cfg,
        filters=Filters(validated_only=True, allow_placeholder=True),
    )
    # Nothing in the fixture corpus is signed off, so a validated-only query is empty.
    assert result.hits == []
    assert result.should_abstain


def test_placeholder_filter_excludes_placeholder_chunks(built_index, embedder) -> None:
    cfg, store = built_index
    result = retrieve(
        "maize", store, embedder, cfg,
        filters=Filters(allow_placeholder=False),
    )
    assert result.hits == []


def test_both_backends_agree_on_ranking(built_index) -> None:
    """The numpy fallback must not be a different product from sqlite-vec."""
    cfg, store = built_index
    if store.backend != "sqlite-vec":
        pytest.skip("sqlite-vec not available, only one backend to compare")
    query = np.zeros(cfg.embedder.dim, dtype=np.float32)
    query[0] = 1.0
    vec_hits = store.search(query, 3)

    numpy_store = VectorStore(cfg.index.path, cfg.embedder.dim, backend="numpy")
    assert numpy_store.backend == "numpy"
    numpy_hits = numpy_store.search(query, 3)
    numpy_store.close()

    assert [h.chunk_id for h in vec_hits] == [h.chunk_id for h in numpy_hits]
    for a, b in zip(vec_hits, numpy_hits):
        assert a.score == pytest.approx(b.score, abs=1e-4)


# ---------------------------------------------------------------- confidence


def test_no_hits_scores_zero_and_abstains(fixture_config) -> None:
    conf = score_confidence([], fixture_config)
    assert conf.score == 0.0
    assert conf.is_abstain
    assert "no passages" in conf.reason


def test_strong_differentiated_match_scores_high(fixture_config) -> None:
    hits = [
        make_hit("a", chunk_id="c1", score=0.92, doc_id="d1"),
        make_hit("b", chunk_id="c2", score=0.88, doc_id="d2"),
        make_hit("c", chunk_id="c3", score=0.30, doc_id="d3"),
    ]
    conf = score_confidence(hits, fixture_config)
    assert conf.band == "high"
    assert not conf.is_abstain


def test_weak_top1_abstains(fixture_config) -> None:
    hits = [make_hit("a", score=0.12), make_hit("b", chunk_id="c2", score=0.10)]
    conf = score_confidence(hits, fixture_config)
    assert conf.is_abstain
    assert "close to this question" in conf.reason


def test_undifferentiated_set_is_penalised(fixture_config) -> None:
    """A high top1 with an equally high tail is when a model blends passages."""
    flat = [make_hit(str(i), chunk_id=f"c{i}", score=0.70, doc_id=f"d{i}")
            for i in range(5)]
    peaked = [make_hit("0", chunk_id="c0", score=0.70, doc_id="d0")] + [
        make_hit(str(i), chunk_id=f"c{i}", score=0.20, doc_id=f"d{i}")
        for i in range(1, 5)
    ]
    assert score_confidence(flat, fixture_config).score < score_confidence(
        peaked, fixture_config
    ).score


def test_agreement_across_documents_raises_confidence(fixture_config) -> None:
    same_doc = [
        make_hit("a", chunk_id="c1", score=0.80, doc_id="d1"),
        make_hit("b", chunk_id="c2", score=0.78, doc_id="d1", crop="sorghum"),
    ]
    cross_doc = [
        make_hit("a", chunk_id="c1", score=0.80, doc_id="d1"),
        make_hit("b", chunk_id="c2", score=0.78, doc_id="d2", crop="sorghum"),
    ]
    assert score_confidence(cross_doc, fixture_config).agreement > score_confidence(
        same_doc, fixture_config
    ).agreement


def test_threshold_boundary_is_exact(fixture_config) -> None:
    """Just below abstain_below abstains, just above does not. No fuzzy middle."""
    cfg = fixture_config
    below = dataclasses.replace(
        cfg.retrieval, abstain_below=0.99, band_medium=0.99, band_high=0.995
    )
    cfg_high = dataclasses.replace(cfg, retrieval=below)
    hits = [make_hit("a", score=0.90), make_hit("b", chunk_id="c2", score=0.10)]
    assert score_confidence(hits, cfg_high).is_abstain

    above = dataclasses.replace(cfg.retrieval, abstain_below=0.01, band_medium=0.02,
                                band_high=0.03)
    cfg_low = dataclasses.replace(cfg, retrieval=above)
    assert not score_confidence(hits, cfg_low).is_abstain


def test_single_hit_gets_neutral_margin_not_free_credit(fixture_config) -> None:
    single = score_confidence([make_hit("a", score=0.60)], fixture_config)
    paired = score_confidence(
        [make_hit("a", score=0.60), make_hit("b", chunk_id="c2", score=0.59)],
        fixture_config,
    )
    assert single.score > paired.score  # an undifferentiated pair is worse evidence
    assert single.score < 0.60 + 0.25 + 0.15  # but not a full-credit score


# ---------------------------------------------------------------- region handling


@pytest.mark.parametrize(
    "query,expected",
    [
        ("when should I plant maize in Matabeleland North", ("matabeleland-north",)),
        ("planting in Mashonaland Central", ("mashonaland-central",)),
        ("planting in mashonaland-west", ("mashonaland-west",)),
        ("what about Manicaland", ("manicaland",)),
        ("when should I plant maize in Mashonaland",
         ("mashonaland-central", "mashonaland-east", "mashonaland-west")),
        ("Matabeleland conditions", ("matabeleland-north", "matabeleland-south")),
        ("when should I plant maize", ()),
        ("how do I store grain", ()),
    ],
)
def test_region_detection(query: str, expected: tuple) -> None:
    assert detect_regions(query) == expected


def test_specific_region_does_not_pull_in_its_siblings() -> None:
    """'Mashonaland Central' must not also match East and West."""
    assert detect_regions("maize in Mashonaland East") == ("mashonaland-east",)


def test_a_named_region_excludes_other_regions(built_index, embedder) -> None:
    """The near-miss that matters most: one region's calendar is wrong in another."""
    cfg, store = built_index
    result = retrieve("when should I plant maize in Matabeleland North",
                      store, embedder, cfg)
    for hit in result.hits:
        assert hit.region in ("matabeleland-north", "national"), (
            f"a {hit.region} passage was served for a Matabeleland North question"
        )


def test_a_named_region_still_reaches_its_own_content(built_index, embedder) -> None:
    cfg, store = built_index
    result = retrieve("when should I plant maize in Mashonaland Central",
                      store, embedder, cfg)
    assert any(h.region == "mashonaland-central" for h in result.hits)


def test_explicit_filter_overrides_detection(built_index, embedder) -> None:
    cfg, store = built_index
    result = retrieve(
        "when should I plant maize in Matabeleland North", store, embedder, cfg,
        filters=Filters(region="mashonaland-central", allow_placeholder=True),
    )
    assert result.filters_used.all_regions() == ("mashonaland-central",)


def test_multi_region_filter_matches_any_of_them(built_index, embedder) -> None:
    cfg, store = built_index
    result = retrieve(
        "planting window", store, embedder, cfg,
        filters=Filters(regions=("mashonaland-central", "manicaland"),
                        allow_placeholder=True),
    )
    for hit in result.hits:
        assert hit.region in ("mashonaland-central", "manicaland", "national")
