"""Generation backends, prompts, and the device budget.

These run against the stub backend so the suite never depends on model weights, which is
also why a safety property proven here is a property of the system rather than of one
particular model.
"""

from __future__ import annotations

import dataclasses

import pytest

from mhizha.errors import BackendUnavailableError
from mhizha.llm.base import GenerationRequest, LLMBackend
from mhizha.llm.loader import load_backend
from mhizha.llm.prompts import INSUFFICIENT, build_prompt
from mhizha.llm.registry import SHORTLIST, budget_report, fits_profile, resolve, select
from mhizha.llm.stub import StubBackend

from conftest import make_hit


# ---------------------------------------------------------------- prompts


def test_prompt_contains_only_retrieved_passages() -> None:
    hits = [make_hit("Passage one text.", chunk_id="c1"),
            make_hit("Passage two text.", chunk_id="c2")]
    grounded = build_prompt("when to plant", hits, "en")
    assert "Passage one text." in grounded.prompt
    assert "Passage two text." in grounded.prompt
    assert set(grounded.passage_map) == {"P1", "P2"}


def test_prompt_maps_passage_ids_to_chunk_ids() -> None:
    hits = [make_hit("x", chunk_id="chunk-abc")]
    grounded = build_prompt("q", hits, "en")
    assert grounded.chunk_id_for("P1") == "chunk-abc"
    assert grounded.chunk_id_for("P4") is None


def test_prompt_forbids_outside_knowledge_and_offers_an_out() -> None:
    grounded = build_prompt("q", [make_hit("x")], "en")
    assert "ONLY from the numbered passages" in grounded.system
    assert INSUFFICIENT in grounded.system
    assert "dosage" in grounded.system.lower()


def test_prompt_carries_passage_metadata_for_qualification() -> None:
    """Without region on the passage, a regional recommendation flattens to national."""
    hits = [make_hit("text", crop="maize")]
    grounded = build_prompt("q", hits, "en")
    assert "region=national" in grounded.prompt
    assert "crop=maize" in grounded.prompt


@pytest.mark.parametrize("lang", ["en", "sn", "nd"])
def test_every_locale_has_a_system_prompt(lang: str) -> None:
    grounded = build_prompt("q", [make_hit("x")], lang)
    assert "Mhizha" in grounded.system
    assert INSUFFICIENT in grounded.system


# ---------------------------------------------------------------- stub backend


def test_stub_satisfies_the_backend_protocol() -> None:
    assert isinstance(StubBackend(), LLMBackend)


def test_stub_is_deterministic() -> None:
    hits = [make_hit("Planting follows the onset of effective rains in this region.")]
    grounded = build_prompt("when does planting follow the rains", hits, "en")
    request = GenerationRequest(grounded.system, grounded.prompt, 200, 0.0, 1729)
    backend = StubBackend()
    first = backend.generate(request).text
    second = backend.generate(request).text
    assert first == second


def test_stub_only_emits_text_present_in_the_passages() -> None:
    """The stub is the floor: anything the real model does worse than this is a bug."""
    passage = "Planting follows the onset of effective rains in this region."
    grounded = build_prompt("when does planting follow the rains", [make_hit(passage)], "en")
    result = StubBackend().generate(
        GenerationRequest(grounded.system, grounded.prompt, 200, 0.0, 1729)
    )
    body = result.text.replace("[P1]", "").strip().rstrip(".")
    assert body.lower() in passage.lower()


def test_stub_cites_a_passage_id() -> None:
    grounded = build_prompt(
        "rains onset planting", [make_hit("Planting follows the onset of rains here.")], "en"
    )
    result = StubBackend().generate(
        GenerationRequest(grounded.system, grounded.prompt, 200, 0.0, 1729)
    )
    assert "[P1]" in result.text


def test_stub_reports_insufficient_when_nothing_overlaps() -> None:
    grounded = build_prompt(
        "quinoa irrigation scheduling", [make_hit("Completely unrelated tractor text.")], "en"
    )
    result = StubBackend().generate(
        GenerationRequest(grounded.system, grounded.prompt, 200, 0.0, 1729)
    )
    assert result.text == INSUFFICIENT


# ---------------------------------------------------------------- registry


def test_no_model_fits_when_the_budget_is_tiny(fixture_config) -> None:
    tiny = dataclasses.replace(fixture_config.device, app_budget_mb=300)
    cfg = dataclasses.replace(fixture_config, device=tiny)
    assert resolve(cfg) == []


def test_four_gb_profile_excludes_the_larger_models(fixture_config) -> None:
    """A model that needs 2.3 GB does not 'mostly work' on a 4 GB phone."""
    assert fixture_config.device.key == "low_4gb"
    fitting = {m.id for m in resolve(fixture_config)}
    assert "llama-3.2-1b-instruct-q4_k_m" in fitting
    assert "phi-3-mini-4k-instruct-q4" not in fitting
    assert "llama-3.2-3b-instruct-q4_k_m" not in fitting


def test_six_gb_profile_admits_more(fixture_config) -> None:
    mid = fixture_config.device_profiles["mid_6gb"]
    fitting = {
        m.id for m in SHORTLIST
        if fits_profile(m, mid, embedder_mb=fixture_config.embedder.est_size_mb)
    }
    assert "gemma-2-2b-it-q4_k_m" in fitting


def test_selection_prefers_the_largest_model_that_fits(fixture_config) -> None:
    chosen = select(fixture_config)
    assert chosen is not None
    fitting = resolve(fixture_config)
    assert chosen.resident_mb == max(m.resident_mb for m in fitting)


def test_unknown_configured_model_raises(fixture_config) -> None:
    llm = dataclasses.replace(fixture_config.llm, model_id="not-a-real-model")
    cfg = dataclasses.replace(fixture_config, llm=llm)
    with pytest.raises(KeyError, match="registry"):
        select(cfg)


def test_budget_report_accounts_for_every_component(fixture_config) -> None:
    smallest = min(SHORTLIST, key=lambda m: m.resident_mb)
    report = budget_report(fixture_config, index_mb=12.0, model=smallest)
    components = {line.component for line in report.lines}
    assert components == {"LLM weights", "KV cache", "embedder", "index",
                          "runtime overhead"}
    assert report.total_mb == pytest.approx(sum(l.mb for l in report.lines))


def test_selected_model_fits_the_active_profile(fixture_config) -> None:
    report = budget_report(fixture_config, index_mb=2.0)
    assert report.fits, (
        f"selected {report.model.id if report.model else None} needs "
        f"{report.total_mb:.0f} MB against a {fixture_config.device.app_budget_mb} MB budget"
    )


def test_four_gb_margin_is_thin_and_index_growth_can_break_it(fixture_config) -> None:
    """Documents a real constraint rather than hiding it.

    On the 4 GB profile the smallest candidate leaves single-digit MB of headroom once
    the embedder and a small index are counted. A corpus that grows the index past
    roughly 10 MB pushes the profile over budget, at which point the answer is a smaller
    model or a smaller index, not a bigger budget number in config.yaml.
    """
    smallest = min(SHORTLIST, key=lambda m: m.resident_mb)
    tight = budget_report(fixture_config, index_mb=2.0, model=smallest)
    grown = budget_report(fixture_config, index_mb=40.0, model=smallest)
    assert tight.fits
    assert not grown.fits, (
        "the 4 GB budget unexpectedly absorbed a 40 MB index. If the profile numbers "
        "changed, re-measure them on hardware (data/SOURCES.md gap G-09)."
    )
    assert tight.headroom_mb < 100


def test_unverified_sizes_are_labelled_as_such() -> None:
    """An estimate presented as a measurement is how an oversized model ships."""
    for model in SHORTLIST:
        if not model.verified:
            assert "(approx, unverified)" in model.size_label


def test_every_candidate_declares_a_licence() -> None:
    for model in SHORTLIST:
        assert model.licence.strip()


# ---------------------------------------------------------------- loader


def test_loader_returns_the_stub_by_default(fixture_config) -> None:
    assert load_backend(fixture_config).name == "stub"


def test_unknown_backend_raises_with_the_known_list(fixture_config) -> None:
    with pytest.raises(BackendUnavailableError, match="stub, llamacpp"):
        load_backend(fixture_config, backend="tensorrt")


def test_llamacpp_without_weights_fails_clearly(fixture_config) -> None:
    """No runtime download path exists, so a missing GGUF must say what to do."""
    with pytest.raises(BackendUnavailableError):
        load_backend(fixture_config, backend="llamacpp")
