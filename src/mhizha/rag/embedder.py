"""RUNTIME (offline). Local sentence embedding.

Loads a sentence-transformers model from a local directory. There is no cloud embedding
path, at build time or at runtime, and adding one would violate rule 1.

A deterministic hash embedder is available as a fallback so the test suite and a fresh
checkout never depend on a model download. It produces stable, meaningless vectors: it
proves the pipeline works, it does not produce useful retrieval, and config.py forbids
it in the production profile.
"""

from __future__ import annotations

import hashlib
from typing import Protocol

import numpy as np

from ..config import EmbedderConfig


class Embedder(Protocol):
    id: str
    dim: int

    def encode(self, texts: list[str]) -> np.ndarray: ...


def _l2_normalise(matrix: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return matrix / norms


class HashEmbedder:
    """Deterministic bag-of-hashed-tokens embedder. Fallback only, never production."""

    def __init__(self, dim: int, model_id: str = "hash-fallback") -> None:
        self.dim = dim
        self.id = model_id

    def encode(self, texts: list[str]) -> np.ndarray:
        out = np.zeros((len(texts), self.dim), dtype=np.float32)
        for row, text in enumerate(texts):
            for token in text.lower().split():
                digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
                bucket = int.from_bytes(digest[:4], "big") % self.dim
                sign = 1.0 if digest[4] % 2 == 0 else -1.0
                out[row, bucket] += sign
        return _l2_normalise(out)


class SentenceTransformerEmbedder:
    """Wraps a locally-stored sentence-transformers model. No download at load time."""

    def __init__(self, cfg: EmbedderConfig) -> None:
        from sentence_transformers import SentenceTransformer

        self._model = SentenceTransformer(str(cfg.path))
        self.id = cfg.id
        self.dim = cfg.dim
        self._normalize = cfg.normalize

    def encode(self, texts: list[str]) -> np.ndarray:
        vectors = self._model.encode(
            texts,
            convert_to_numpy=True,
            normalize_embeddings=self._normalize,
            show_progress_bar=False,
        )
        return np.asarray(vectors, dtype=np.float32)


def active_embedder_id(cfg: EmbedderConfig) -> str:
    """Which embedder `load_embedder` would use, without loading it.

    Exists so a capture or a report can state its own provenance. Duplicating the
    weights-present check at each call site is how the answer drifts from the truth.
    """
    if cfg.path.is_dir() and any(cfg.path.iterdir()):
        return cfg.id
    return f"hash-fallback:{cfg.dim}" if cfg.allow_hash_fallback else "unavailable"


def load_embedder(cfg: EmbedderConfig) -> Embedder:
    """Load the configured embedder, or the hash fallback when weights are absent."""
    weights_present = cfg.path.is_dir() and any(cfg.path.iterdir())
    if weights_present:
        try:
            return SentenceTransformerEmbedder(cfg)
        except ImportError:
            if not cfg.allow_hash_fallback:
                raise
    elif not cfg.allow_hash_fallback:
        from ..errors import BackendUnavailableError

        raise BackendUnavailableError(
            f"embedder weights not found at {cfg.path}.\n"
            f"  Fetch them once, at build time:  make embedder\n"
            f"  (or `make setup`, which now does it for you)\n"
            f"  Refusing rather than falling back to the hash embedder: it would answer, "
            f"but with different retrieval than every figure and capture in this "
            f"repository, and nothing on screen would say so."
        )
    return HashEmbedder(cfg.dim, model_id=f"hash-fallback:{cfg.dim}")


def embed_chunk_text(text: str, *, crop: str, region: str, season: str) -> str:
    """Prefix a chunk with compact metadata before embedding.

    A query naming a region should reach a passage whose region appears only in its
    document heading, which the chunk text itself may not repeat.
    """
    prefix_parts = [p for p in (crop, region, season) if p and p != "unspecified"]
    prefix = " | ".join(prefix_parts)
    return f"{prefix}\n{text}" if prefix else text
