"""RUNTIME (offline). Backend selection from config. No model name is hardcoded here."""

from __future__ import annotations

from ..config import Config
from ..errors import BackendUnavailableError
from .base import LLMBackend
from .registry import select
from .stub import StubBackend


def load_backend(cfg: Config, *, backend: str | None = None) -> LLMBackend:
    """Instantiate the configured generation backend."""
    name = backend or cfg.llm.backend

    if name == "stub":
        return StubBackend()

    if name == "llamacpp":
        from .llamacpp import LlamaCppBackend

        candidate = select(cfg)
        if candidate is None:
            raise BackendUnavailableError(
                f"no model in the registry fits the {cfg.device.key} profile "
                f"({cfg.device.weights_budget_mb} MB for weights). Run `make models`."
            )
        model_path = cfg.llm.model_dir / f"{candidate.id}.gguf"
        runtime = cfg.device.runtime
        return LlamaCppBackend(
            model_path,
            context_tokens=cfg.llm.context_tokens,
            seed=cfg.llm.seed,
            threads=runtime.threads,
            mlock=runtime.mlock,
            n_gpu_layers=runtime.n_gpu_layers,
        )

    raise BackendUnavailableError(
        f"unknown llm.backend {name!r}. Known backends: stub, llamacpp. "
        "Android runtimes (MediaPipe, MLC-LLM) are documented in "
        "docs/android-packaging.md and implement the same protocol."
    )
