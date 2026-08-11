"""RUNTIME (offline). Typed config loader. The single source of truth.

Nothing else in the codebase reads config.yaml directly. Import `load_config()` and
read attributes, so that a renamed key breaks in one place instead of five.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from .errors import ConfigError

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_PATH = REPO_ROOT / "config.yaml"


@dataclass(frozen=True)
class ProfileRuntime:
    """Per-profile inference hints. Optional: phone profiles do not set these.

    These exist because the ADTC judged environment pins values we would otherwise
    leave to the host (4 vCPU, CPU-only, mlock). Carrying them on the device profile
    keeps the competition settings out of the product code path entirely.
    """

    backend: str | None = None
    threads: int | None = None
    mlock: bool = False
    n_gpu_layers: int = 0


@dataclass(frozen=True)
class DeviceProfile:
    key: str
    label: str
    total_ram_mb: int
    app_budget_mb: int
    kv_cache_mb: int
    runtime_overhead_mb: int
    runtime: ProfileRuntime = field(default_factory=ProfileRuntime)

    @property
    def weights_budget_mb(self) -> int:
        """Memory left for model weights, embedder, and index once fixed costs are paid."""
        return self.app_budget_mb - self.kv_cache_mb - self.runtime_overhead_mb


@dataclass(frozen=True)
class EmbedderConfig:
    id: str
    path: Path
    dim: int
    normalize: bool
    multilingual: bool
    est_size_mb: int
    allow_hash_fallback: bool

    @property
    def weights_present(self) -> bool:
        return self.path.exists() and any(self.path.iterdir()) if self.path.is_dir() else False


@dataclass(frozen=True)
class LLMConfig:
    backend: str
    model_id: str | None
    model_dir: Path
    context_tokens: int
    max_output_tokens: int
    temperature: float
    seed: int


@dataclass(frozen=True)
class RetrievalConfig:
    top_k: int
    abstain_below: float
    min_margin: float
    validated_only: bool
    allow_placeholder: bool
    band_high: float
    band_medium: float


@dataclass(frozen=True)
class ChunkConfig:
    target_chars: int
    max_chars: int
    overlap_chars: int
    respect_tables: bool


@dataclass(frozen=True)
class CorpusConfig:
    dir: Path
    raw_dir: Path
    review_ledger: Path
    chunk: ChunkConfig


@dataclass(frozen=True)
class IndexConfig:
    path: Path
    schema_version: int


@dataclass(frozen=True)
class I18nConfig:
    default_lang: str
    languages: tuple[str, ...]
    locales_dir: Path


@dataclass(frozen=True)
class SafetyConfig:
    require_citations: bool
    agrochemical_guard: bool
    quantity_proximity_chars: int
    trigger_terms: tuple[str, ...]
    quantity_units: tuple[str, ...]


@dataclass(frozen=True)
class Config:
    profile: str
    device: DeviceProfile
    device_profiles: dict[str, DeviceProfile]
    embedder: EmbedderConfig
    llm: LLMConfig
    retrieval: RetrievalConfig
    corpus: CorpusConfig
    index: IndexConfig
    i18n: I18nConfig
    safety: SafetyConfig
    source_path: Path = field(default=DEFAULT_CONFIG_PATH)

    @property
    def is_production(self) -> bool:
        return self.profile == "production"


def _abs(p: str | Path) -> Path:
    path = Path(p)
    return path if path.is_absolute() else REPO_ROOT / path


def _require(d: dict[str, Any], key: str, where: str) -> Any:
    if key not in d:
        raise ConfigError(f"config.yaml: missing required key '{key}' under {where}")
    return d[key]


def load_config(path: str | Path | None = None) -> Config:
    """Load and validate config. Raises ConfigError rather than defaulting silently."""
    cfg_path = _abs(path or os.environ.get("MHIZHA_CONFIG") or DEFAULT_CONFIG_PATH)
    if not cfg_path.exists():
        raise ConfigError(f"config not found at {cfg_path}")

    raw = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}

    profile = raw.get("profile", "dev")
    if profile not in ("dev", "production"):
        raise ConfigError(f"profile must be 'dev' or 'production', got {profile!r}")

    dev_raw = _require(raw, "device", "root")
    active = _require(dev_raw, "active_profile", "device")
    profiles_raw = _require(dev_raw, "profiles", "device")
    if active not in profiles_raw:
        raise ConfigError(
            f"device.active_profile {active!r} is not defined in device.profiles"
        )
    profiles = {
        key: DeviceProfile(
            key=key,
            label=p["label"],
            total_ram_mb=int(p["total_ram_mb"]),
            app_budget_mb=int(p["app_budget_mb"]),
            kv_cache_mb=int(p["kv_cache_mb"]),
            runtime_overhead_mb=int(p["runtime_overhead_mb"]),
            runtime=ProfileRuntime(
                backend=(p.get("runtime") or {}).get("backend"),
                threads=(p.get("runtime") or {}).get("threads"),
                mlock=bool((p.get("runtime") or {}).get("mlock", False)),
                n_gpu_layers=int((p.get("runtime") or {}).get("n_gpu_layers", 0)),
            ),
        )
        for key, p in profiles_raw.items()
    }

    emb_raw = _require(raw, "embedder", "root")
    embedder = EmbedderConfig(
        id=emb_raw["id"],
        path=_abs(emb_raw["path"]),
        dim=int(emb_raw["dim"]),
        normalize=bool(emb_raw.get("normalize", True)),
        multilingual=bool(emb_raw.get("multilingual", False)),
        est_size_mb=int(emb_raw.get("est_size_mb", 0)),
        allow_hash_fallback=bool(emb_raw.get("allow_hash_fallback", True)),
    )

    llm_raw = _require(raw, "llm", "root")
    llm = LLMConfig(
        backend=llm_raw.get("backend", "stub"),
        model_id=llm_raw.get("model_id"),
        model_dir=_abs(llm_raw.get("model_dir", "models/llm")),
        context_tokens=int(llm_raw.get("context_tokens", 2048)),
        max_output_tokens=int(llm_raw.get("max_output_tokens", 400)),
        temperature=float(llm_raw.get("temperature", 0.0)),
        seed=int(llm_raw.get("seed", 1729)),
    )

    ret_raw = _require(raw, "retrieval", "root")
    bands = ret_raw.get("bands", {})
    retrieval = RetrievalConfig(
        top_k=int(ret_raw.get("top_k", 5)),
        abstain_below=float(_require(ret_raw, "abstain_below", "retrieval")),
        min_margin=float(ret_raw.get("min_margin", 0.0)),
        validated_only=bool(ret_raw.get("validated_only", False)),
        allow_placeholder=bool(ret_raw.get("allow_placeholder", False)),
        band_high=float(bands.get("high", 0.75)),
        band_medium=float(bands.get("medium", 0.55)),
    )

    cor_raw = _require(raw, "corpus", "root")
    ch = cor_raw.get("chunk", {})
    corpus = CorpusConfig(
        dir=_abs(cor_raw.get("dir", "data/corpus")),
        raw_dir=_abs(cor_raw.get("raw_dir", "data/raw")),
        review_ledger=_abs(cor_raw.get("review_ledger", "data/review_ledger.jsonl")),
        chunk=ChunkConfig(
            target_chars=int(ch.get("target_chars", 700)),
            max_chars=int(ch.get("max_chars", 1100)),
            overlap_chars=int(ch.get("overlap_chars", 120)),
            respect_tables=bool(ch.get("respect_tables", True)),
        ),
    )

    idx_raw = raw.get("index", {})
    index = IndexConfig(
        path=_abs(idx_raw.get("path", "data/index/mhizha.db")),
        schema_version=int(idx_raw.get("schema_version", 1)),
    )

    i18n_raw = raw.get("i18n", {})
    i18n = I18nConfig(
        default_lang=i18n_raw.get("default_lang", "en"),
        languages=tuple(i18n_raw.get("languages", ["en"])),
        locales_dir=_abs(i18n_raw.get("locales_dir", "src/mhizha/i18n/locales")),
    )

    saf_raw = raw.get("safety", {})
    safety = SafetyConfig(
        require_citations=bool(saf_raw.get("require_citations", True)),
        agrochemical_guard=bool(saf_raw.get("agrochemical_guard", True)),
        quantity_proximity_chars=int(saf_raw.get("quantity_proximity_chars", 120)),
        trigger_terms=tuple(t.lower() for t in saf_raw.get("trigger_terms", [])),
        quantity_units=tuple(u.lower() for u in saf_raw.get("quantity_units", [])),
    )

    cfg = Config(
        profile=profile,
        device=profiles[active],
        device_profiles=profiles,
        embedder=embedder,
        llm=llm,
        retrieval=retrieval,
        corpus=corpus,
        index=index,
        i18n=i18n,
        safety=safety,
        source_path=cfg_path,
    )
    _validate_profile_invariants(cfg)
    return cfg


def _validate_profile_invariants(cfg: Config) -> None:
    """Rules that must hold in production, checked here so they cannot be forgotten."""
    if not cfg.is_production:
        return
    problems: list[str] = []
    if cfg.retrieval.allow_placeholder:
        problems.append("retrieval.allow_placeholder must be false in production")
    if not cfg.retrieval.validated_only:
        problems.append("retrieval.validated_only must be true in production")
    if cfg.embedder.allow_hash_fallback:
        problems.append("embedder.allow_hash_fallback must be false in production")
    if not cfg.safety.require_citations:
        problems.append("safety.require_citations must be true in production")
    if not cfg.safety.agrochemical_guard:
        problems.append("safety.agrochemical_guard must be true in production")
    if problems:
        raise ConfigError("production profile violations:\n  - " + "\n  - ".join(problems))


@lru_cache(maxsize=1)
def get_config() -> Config:
    """Cached config for CLI use. Tests should call load_config() directly."""
    return load_config()
