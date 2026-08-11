"""RUNTIME (offline). Candidate model shortlist and RAM budget resolution.

The shortlist is data, not branching logic: adding a model means adding a row. No model
name appears anywhere else in the codebase except config.yaml.

Every size figure below is marked `(approx, unverified)` until it has been measured on
target hardware. An estimate presented as a measurement is how a model that does not fit
ends up shipped to a farmer with no signal.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..config import Config, DeviceProfile


@dataclass(frozen=True)
class ModelCandidate:
    id: str
    params_b: float
    quant: str
    file_mb: int          # on-disk GGUF size
    resident_mb: int      # approximate resident weights, excludes KV cache
    context_tokens: int
    licence: str
    gguf_hint: str
    verified: bool = False  # set True only once measured on a real device
    note: str = ""

    @property
    def size_label(self) -> str:
        suffix = "" if self.verified else " (approx, unverified)"
        return f"{self.file_mb} MB on disk, ~{self.resident_mb} MB resident{suffix}"


# Sizes are typical published GGUF sizes for these quantizations. None have been
# measured on a Zimbabwean target handset yet. See data/SOURCES.md gap G-09.
SHORTLIST: tuple[ModelCandidate, ...] = (
    ModelCandidate(
        id="llama-3.2-1b-instruct-q4_k_m",
        params_b=1.24, quant="Q4_K_M", file_mb=810, resident_mb=900,
        context_tokens=8192, licence="Llama 3.2 Community License",
        gguf_hint="bartowski/Llama-3.2-1B-Instruct-GGUF",
        note="Smallest credible instruct model. Best headroom on a 4 GB device.",
    ),
    ModelCandidate(
        id="qwen2.5-1.5b-instruct-q4_k_m",
        params_b=1.54, quant="Q4_K_M", file_mb=1000, resident_mb=1100,
        context_tokens=32768, licence="Apache-2.0",
        gguf_hint="Qwen/Qwen2.5-1.5B-Instruct-GGUF",
        note="Apache-2.0 is the least restrictive licence in this list. Long context.",
    ),
    ModelCandidate(
        id="smollm2-1.7b-instruct-q4_k_m",
        params_b=1.71, quant="Q4_K_M", file_mb=1060, resident_mb=1160,
        context_tokens=8192, licence="Apache-2.0",
        gguf_hint="HuggingFaceTB/SmolLM2-1.7B-Instruct-GGUF",
        note="Trained for on-device use. Weaker at long grounded extraction.",
    ),
    ModelCandidate(
        id="gemma-2-2b-it-q4_k_m",
        params_b=2.61, quant="Q4_K_M", file_mb=1710, resident_mb=1850,
        context_tokens=8192, licence="Gemma Terms of Use",
        gguf_hint="bartowski/gemma-2-2b-it-GGUF",
        note="Does not fit the 4 GB profile. Viable at 6 GB.",
    ),
    ModelCandidate(
        id="llama-3.2-3b-instruct-q4_k_m",
        params_b=3.21, quant="Q4_K_M", file_mb=2020, resident_mb=2200,
        context_tokens=8192, licence="Llama 3.2 Community License",
        gguf_hint="bartowski/Llama-3.2-3B-Instruct-GGUF",
        note="6 GB profile and above.",
    ),
    ModelCandidate(
        id="phi-3-mini-4k-instruct-q4",
        params_b=3.82, quant="Q4_K_M", file_mb=2320, resident_mb=2500,
        context_tokens=4096, licence="MIT",
        gguf_hint="microsoft/Phi-3-mini-4k-instruct-gguf",
        note="Strong for its size but out of budget at 4 GB.",
    ),
)

BY_ID = {m.id: m for m in SHORTLIST}


@dataclass(frozen=True)
class BudgetLine:
    component: str
    mb: float
    note: str = ""


@dataclass
class BudgetReport:
    profile: DeviceProfile
    lines: list[BudgetLine]
    model: ModelCandidate | None

    @property
    def total_mb(self) -> float:
        return sum(line.mb for line in self.lines)

    @property
    def fits(self) -> bool:
        return self.total_mb <= self.profile.app_budget_mb

    @property
    def headroom_mb(self) -> float:
        return self.profile.app_budget_mb - self.total_mb


def fits_profile(model: ModelCandidate, profile: DeviceProfile, *,
                 embedder_mb: float = 0.0, index_mb: float = 0.0) -> bool:
    used = model.resident_mb + embedder_mb + index_mb
    return used <= profile.weights_budget_mb


def resolve(cfg: Config, *, embedder_mb: float | None = None,
            index_mb: float = 0.0) -> list[ModelCandidate]:
    """Candidates that fit the active device profile, largest first.

    Largest first because within the budget, more parameters is the better bet for
    grounded extraction quality. The budget itself is the only hard filter.
    """
    emb = cfg.embedder.est_size_mb if embedder_mb is None else embedder_mb
    fitting = [
        m for m in SHORTLIST
        if fits_profile(m, cfg.device, embedder_mb=emb, index_mb=index_mb)
    ]
    return sorted(fitting, key=lambda m: m.resident_mb, reverse=True)


def select(cfg: Config, *, index_mb: float = 0.0) -> ModelCandidate | None:
    """The configured model if set and it fits, otherwise the best fitting candidate."""
    if cfg.llm.model_id:
        candidate = BY_ID.get(cfg.llm.model_id)
        if candidate is None:
            raise KeyError(
                f"llm.model_id {cfg.llm.model_id!r} is not in the registry shortlist. "
                f"Add it to registry.SHORTLIST with its measured size."
            )
        return candidate
    fitting = resolve(cfg, index_mb=index_mb)
    return fitting[0] if fitting else None


def budget_report(cfg: Config, *, index_mb: float = 0.0,
                  model: ModelCandidate | None = None) -> BudgetReport:
    """Full memory accounting against the active device profile."""
    chosen = model if model is not None else select(cfg, index_mb=index_mb)
    lines = [
        BudgetLine("runtime overhead", cfg.device.runtime_overhead_mb,
                   "app, interpreter, framework"),
        BudgetLine("KV cache", cfg.device.kv_cache_mb,
                   f"at {cfg.llm.context_tokens} context tokens"),
        BudgetLine("embedder", cfg.embedder.est_size_mb, cfg.embedder.id),
        BudgetLine("index", index_mb, "sqlite file, mapped where possible"),
    ]
    if chosen is not None:
        lines.insert(0, BudgetLine("LLM weights", chosen.resident_mb,
                                   f"{chosen.id} {chosen.quant}"))
    return BudgetReport(profile=cfg.device, lines=lines, model=chosen)
