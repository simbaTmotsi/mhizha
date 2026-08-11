"""RUNTIME (offline) for `open_index`; the build path runs at BUILD TIME.

Neither path touches the network: `build_index` embeds with a locally-stored model, so
this module is safe to ship even though only `open_index` is used on the device.

The index is a derived artefact: fully rebuildable from data/corpus/ and config.yaml
alone, and gitignored. Nothing may be true of the index that is not recoverable from
the corpus.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from ..config import Config
from ..corpus.schema import Chunk, chunks_from_json
from ..errors import IndexError_
from .embedder import embed_chunk_text, load_embedder
from .store import SCHEMA_VERSION, VectorStore


@dataclass
class BuildReport:
    chunk_count: int
    dim: int
    backend: str
    file_size_bytes: int
    corpus_sha256: str
    embedder_id: str
    validated_count: int
    placeholder_count: int

    @property
    def file_size_mb(self) -> float:
        return self.file_size_bytes / (1024 * 1024)


def load_chunk_files(corpus_dir: Path) -> list[Chunk]:
    """Load every *.chunks.json produced by the embed step."""
    chunks: list[Chunk] = []
    for path in sorted(corpus_dir.glob("*.chunks.json")):
        chunks.extend(chunks_from_json(path.read_text(encoding="utf-8")))
    return chunks


def corpus_snapshot_hash(chunks: list[Chunk]) -> str:
    """Stable hash of corpus content, so an eval result can name what it ran against."""
    digest = hashlib.sha256()
    for chunk in sorted(chunks, key=lambda c: c.chunk_id):
        digest.update(chunk.chunk_id.encode("utf-8"))
        digest.update(chunk.text_sha256.encode("utf-8"))
    return digest.hexdigest()


def build_index(cfg: Config, chunks: list[Chunk] | None = None) -> BuildReport:
    """BUILD TIME. Embed chunks and write the single-file index."""
    chunks = chunks if chunks is not None else load_chunk_files(cfg.corpus.dir)
    if not chunks:
        raise IndexError_(
            f"no chunks found in {cfg.corpus.dir}. Run `make ingest && make embed` first."
        )

    embedder = load_embedder(cfg.embedder)
    texts = [
        embed_chunk_text(c.text, crop=c.crop, region=c.region, season=c.season)
        for c in chunks
    ]
    vectors = embedder.encode(texts)
    if vectors.shape[1] != cfg.embedder.dim:
        raise IndexError_(
            f"embedder produced dim {vectors.shape[1]} but config declares "
            f"{cfg.embedder.dim}. Fix config.yaml rather than the vectors."
        )

    store = VectorStore(cfg.index.path, cfg.embedder.dim)
    store.create()
    store.clear()
    store.add((c.to_row() for c in chunks), vectors)

    snapshot = corpus_snapshot_hash(chunks)
    store.set_meta("schema_version", str(SCHEMA_VERSION))
    store.set_meta("embedder_id", embedder.id)
    store.set_meta("embedder_dim", str(embedder.dim))
    store.set_meta("normalized", str(cfg.embedder.normalize))
    store.set_meta("corpus_sha256", snapshot)
    store.set_meta("built_at", datetime.now(timezone.utc).isoformat(timespec="seconds"))
    store.set_meta("chunk_count", str(len(chunks)))

    report = BuildReport(
        chunk_count=len(chunks),
        dim=embedder.dim,
        backend=store.backend,
        file_size_bytes=store.file_size_bytes(),
        corpus_sha256=snapshot,
        embedder_id=embedder.id,
        validated_count=sum(1 for c in chunks if c.validated),
        placeholder_count=sum(1 for c in chunks if c.placeholder),
    )
    store.close()
    return report


def open_index(cfg: Config) -> VectorStore:
    """RUNTIME (offline). Open an existing index, verifying the embedder matches."""
    if not cfg.index.path.exists():
        raise IndexError_(
            f"no index at {cfg.index.path}. Build it with `make build` on a developer "
            "machine. The device never builds its own index."
        )
    store = VectorStore(cfg.index.path, cfg.embedder.dim)
    embedder = load_embedder(cfg.embedder)
    store.assert_embedder(embedder.id, embedder.dim)
    return store


def index_stats(cfg: Config) -> dict[str, str]:
    """Everything `make doctor` and `mhizha index --stats` need."""
    if not cfg.index.path.exists():
        return {"status": "missing", "path": str(cfg.index.path)}
    store = VectorStore(cfg.index.path, cfg.embedder.dim)
    stats = {
        "status": "present",
        "path": str(cfg.index.path),
        "backend": store.backend,
        "chunks": str(store.count()),
        "file_size_mb": f"{store.file_size_bytes() / (1024 * 1024):.2f}",
    }
    for key in ("embedder_id", "embedder_dim", "corpus_sha256", "built_at",
                "schema_version"):
        stats[key] = store.get_meta(key, "unknown") or "unknown"
    store.close()
    return stats


def write_chunk_file(path: Path, chunks: list[Chunk]) -> None:
    from ..corpus.schema import chunks_to_json

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(chunks_to_json(chunks), encoding="utf-8")


def dump_json(obj: object) -> str:
    return json.dumps(obj, indent=2, ensure_ascii=False, default=str)
