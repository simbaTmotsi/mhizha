"""RUNTIME (offline). llama-cpp-python backend for the dev harness.

Loads a GGUF from a local path. There is no download path here: the model is placed on
disk at build time. On Android this backend is replaced by MediaPipe LLM Inference or
MLC-LLM behind the same protocol, which is why nothing above this module knows it exists.

Install is optional:  pip install llama-cpp-python
"""

from __future__ import annotations

from pathlib import Path

from ..errors import BackendUnavailableError
from .base import GenerationRequest, GenerationResult


class LlamaCppBackend:
    name = "llamacpp"

    def __init__(
        self,
        model_path: Path,
        *,
        context_tokens: int = 2048,
        threads: int | None = None,
        seed: int = 1729,
        mlock: bool = False,
        n_gpu_layers: int = 0,
    ) -> None:
        try:
            from llama_cpp import Llama
        except ImportError as exc:
            raise BackendUnavailableError(
                "llama-cpp-python is not installed. Run `pip install llama-cpp-python` "
                "(dev harness only), or keep llm.backend: stub in config.yaml."
            ) from exc

        if not model_path.exists():
            raise BackendUnavailableError(
                f"no GGUF at {model_path}. Download a candidate at build time "
                "(`make models` lists them with their sizes) and place it there. "
                "Mhizha never downloads a model at runtime."
            )

        self.model_path = model_path
        self.model_id = model_path.stem
        self._llama = Llama(
            model_path=str(model_path),
            n_ctx=context_tokens,
            n_threads=threads,
            seed=seed,
            verbose=False,
            # Explicitly CPU only by default. Neither the phone nor the ADTC judged
            # laptop has a usable GPU, and llama-bench is pinned -ngl 0 by the profiler.
            n_gpu_layers=n_gpu_layers,
            # mlock keeps weights resident rather than letting them page out. Set by
            # the laptop_8gb profile: the audit box has no swap headroom to spare.
            use_mlock=mlock,
        )

    def resident_mb(self) -> float:
        """On-disk size as a proxy. Resident is higher, so treat this as a floor."""
        return self.model_path.stat().st_size / (1024 * 1024)

    def generate(self, request: GenerationRequest) -> GenerationResult:
        full_prompt = f"{request.system}\n\n{request.prompt}"
        response = self._llama(
            full_prompt,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            stop=list(request.stop) or None,
            echo=False,
        )
        choice = response["choices"][0]
        usage = response.get("usage", {})
        return GenerationResult(
            text=choice["text"].strip(),
            backend=self.name,
            model_id=self.model_id,
            prompt_tokens=usage.get("prompt_tokens", 0),
            output_tokens=usage.get("completion_tokens", 0),
            truncated=choice.get("finish_reason") == "length",
        )
