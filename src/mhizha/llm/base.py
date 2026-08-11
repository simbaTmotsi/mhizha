"""RUNTIME (offline). The generation backend contract.

Every backend implements this protocol so swapping runtime (stub, llama.cpp, MediaPipe
LLM Inference, MLC-LLM) never touches app logic.

One rule holds across all of them: the model is never called without retrieved context.
There is no direct-ask code path, not even behind a debug flag, because a small model
asked an agronomy question with no passages will answer it fluently and wrongly.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class GenerationRequest:
    system: str
    prompt: str
    max_tokens: int
    temperature: float
    seed: int
    stop: tuple[str, ...] = ()


@dataclass(frozen=True)
class GenerationResult:
    text: str
    backend: str
    model_id: str
    prompt_tokens: int = 0
    output_tokens: int = 0
    truncated: bool = False


@runtime_checkable
class LLMBackend(Protocol):
    """A local text generator. Implementations must not touch the network."""

    name: str
    model_id: str

    def generate(self, request: GenerationRequest) -> GenerationResult: ...

    def resident_mb(self) -> float:
        """Approximate resident memory. Used by the budget report in `make doctor`."""
        ...
