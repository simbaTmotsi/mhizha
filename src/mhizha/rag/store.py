"""RUNTIME (offline). Single-file vector store.

One sqlite file holds chunks, metadata, and vectors. That is a deliberate shipping
constraint, not a convenience: the whole retrieval layer has to be copyable into APK
assets and openable read-only by an app with no network permission and no background
service.

Two backends, one file layout:

  sqlite-vec  preferred. k-NN in SQL through a vec0 virtual table.
  numpy       fallback. Brute-force cosine over the same vectors, which are always
              written as BLOBs regardless of backend.

Because vectors are always written as BLOBs, an index built by the fallback is a valid
sqlite-vec index the moment the extension is available, and the reverse also holds.
Callers cannot tell which path is active except through `store.backend`.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import numpy as np

from ..errors import EmbedderMismatchError, IndexError_

SCHEMA_VERSION = 1

# Metadata columns carried on every chunk row. Order matters for the insert statement.
CHUNK_COLUMNS = (
    "chunk_id", "doc_id", "text", "ordinal", "char_start", "char_end", "anchor",
    "source", "publisher", "refresh_date", "lang", "crop", "region", "season",
    "topic", "placeholder", "validated", "text_sha256",
)

_DDL = f"""
CREATE TABLE IF NOT EXISTS chunks (
    rowid       INTEGER PRIMARY KEY,
    {", ".join(f"{c} TEXT" if c not in
       ("ordinal", "char_start", "char_end", "placeholder", "validated")
       else f"{c} INTEGER" for c in CHUNK_COLUMNS)},
    UNIQUE(chunk_id)
);
CREATE INDEX IF NOT EXISTS idx_chunks_crop   ON chunks(crop);
CREATE INDEX IF NOT EXISTS idx_chunks_region ON chunks(region);
CREATE INDEX IF NOT EXISTS idx_chunks_lang   ON chunks(lang);
CREATE INDEX IF NOT EXISTS idx_chunks_valid  ON chunks(validated);

CREATE TABLE IF NOT EXISTS vectors (
    chunk_rowid INTEGER PRIMARY KEY REFERENCES chunks(rowid) ON DELETE CASCADE,
    embedding   BLOB NOT NULL
);

CREATE TABLE IF NOT EXISTS index_meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


@dataclass
class Hit:
    """A retrieved chunk with its similarity score and full provenance."""

    chunk_id: str
    text: str
    score: float
    source: str
    publisher: str
    refresh_date: str
    crop: str
    region: str
    season: str
    topic: str
    lang: str
    anchor: str
    doc_id: str
    placeholder: bool
    validated: bool

    def citation(self) -> str:
        return f"{self.source} ({self.publisher}, refreshed {self.refresh_date})"


@dataclass
class Filters:
    crop: str | None = None
    region: str | None = None
    season: str | None = None
    lang: str | None = None
    validated_only: bool = False
    allow_placeholder: bool = True
    # Several regions at once, for a query naming a province group such as
    # "Mashonaland", which spans three provinces.
    regions: tuple[str, ...] = ()

    def all_regions(self) -> tuple[str, ...]:
        combined = tuple(self.regions)
        if self.region:
            combined = (self.region,) + combined
        return tuple(dict.fromkeys(combined))

    def sql(self) -> tuple[str, list[Any]]:
        clauses: list[str] = []
        params: list[Any] = []
        regions = self.all_regions()
        if regions:
            # 'national' guidance applies everywhere, so never filter it out.
            marks = ", ".join("?" for _ in regions)
            clauses.append(f"(region IN ({marks}) OR region = 'national')")
            params.extend(regions)
        for field_name in ("crop", "season", "lang"):
            value = getattr(self, field_name)
            if value:
                clauses.append(f"{field_name} = ?")
                params.append(value)
        if self.validated_only:
            clauses.append("validated = 1")
        if not self.allow_placeholder:
            clauses.append("placeholder = 0")
        return (" AND ".join(clauses) if clauses else "1=1"), params


def _sqlite_vec_available(conn: sqlite3.Connection) -> bool:
    try:
        import sqlite_vec  # noqa: F401
    except ImportError:
        return False
    try:
        conn.enable_load_extension(True)
        import sqlite_vec

        sqlite_vec.load(conn)
        conn.enable_load_extension(False)
        return True
    except (AttributeError, sqlite3.OperationalError, sqlite3.NotSupportedError):
        return False


class VectorStore:
    """Chunks plus vectors in one sqlite file. Read-only safe on device."""

    def __init__(self, path: Path, dim: int, *, backend: str = "auto") -> None:
        self.path = path
        self.dim = dim
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(path))
        self.conn.row_factory = sqlite3.Row
        self._vec_ok = _sqlite_vec_available(self.conn) if backend != "numpy" else False
        if backend == "sqlite-vec" and not self._vec_ok:
            raise IndexError_(
                "backend 'sqlite-vec' requested but the extension could not be loaded"
            )
        self.backend = "sqlite-vec" if self._vec_ok else "numpy"
        self._matrix: np.ndarray | None = None
        self._rowids: np.ndarray | None = None

    # ------------------------------------------------------------------ lifecycle

    def create(self) -> None:
        self.conn.executescript(_DDL)
        if self._vec_ok:
            self.conn.execute(
                f"CREATE VIRTUAL TABLE IF NOT EXISTS vec_chunks USING vec0("
                f"chunk_rowid INTEGER PRIMARY KEY, "
                f"embedding float[{self.dim}] distance_metric=cosine)"
            )
        self.conn.commit()

    def clear(self) -> None:
        self.conn.executescript(
            "DELETE FROM chunks; DELETE FROM vectors; DELETE FROM index_meta;"
        )
        if self._vec_ok:
            self.conn.execute("DELETE FROM vec_chunks")
        self.conn.commit()
        self._matrix = None

    def close(self) -> None:
        self.conn.close()

    def __enter__(self) -> VectorStore:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    # ------------------------------------------------------------------ metadata

    def set_meta(self, key: str, value: str) -> None:
        self.conn.execute(
            "INSERT INTO index_meta(key, value) VALUES(?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, str(value)),
        )
        self.conn.commit()

    def get_meta(self, key: str, default: str | None = None) -> str | None:
        row = self.conn.execute(
            "SELECT value FROM index_meta WHERE key = ?", (key,)
        ).fetchone()
        return row["value"] if row else default

    def assert_embedder(self, embedder_id: str, dim: int) -> None:
        """Loud failure on mismatch. A silent one produces confident nonsense."""
        stored_id = self.get_meta("embedder_id")
        stored_dim = self.get_meta("embedder_dim")
        if stored_id is None:
            raise IndexError_(
                f"{self.path} has no embedder metadata. Rebuild it with `make index`."
            )
        if stored_id != embedder_id or int(stored_dim or 0) != dim:
            raise EmbedderMismatchError(
                f"index at {self.path} was built with embedder {stored_id!r} "
                f"(dim {stored_dim}), but the configured embedder is {embedder_id!r} "
                f"(dim {dim}). Rebuild the index or restore the original embedder."
            )

    # ------------------------------------------------------------------ writes

    def add(self, rows: Iterable[dict[str, Any]], vectors: np.ndarray) -> int:
        rows = list(rows)
        if len(rows) != len(vectors):
            raise IndexError_(
                f"row/vector count mismatch: {len(rows)} rows, {len(vectors)} vectors"
            )
        if vectors.shape[1] != self.dim:
            raise EmbedderMismatchError(
                f"vector dimension {vectors.shape[1]} does not match store dim {self.dim}"
            )
        placeholders = ", ".join("?" for _ in CHUNK_COLUMNS)
        insert = (
            f"INSERT OR REPLACE INTO chunks ({', '.join(CHUNK_COLUMNS)}) "
            f"VALUES ({placeholders})"
        )
        vectors = np.ascontiguousarray(vectors, dtype=np.float32)
        for row, vector in zip(rows, vectors):
            cursor = self.conn.execute(insert, [row[c] for c in CHUNK_COLUMNS])
            rowid = cursor.lastrowid
            blob = vector.tobytes()
            self.conn.execute(
                "INSERT OR REPLACE INTO vectors(chunk_rowid, embedding) VALUES (?, ?)",
                (rowid, blob),
            )
            if self._vec_ok:
                self.conn.execute(
                    "INSERT OR REPLACE INTO vec_chunks(chunk_rowid, embedding) "
                    "VALUES (?, ?)",
                    (rowid, blob),
                )
        self.conn.commit()
        self._matrix = None
        return len(rows)

    # ------------------------------------------------------------------ reads

    def count(self) -> int:
        return self.conn.execute("SELECT COUNT(*) AS n FROM chunks").fetchone()["n"]

    def file_size_bytes(self) -> int:
        return self.path.stat().st_size if self.path.exists() else 0

    def _load_matrix(self) -> tuple[np.ndarray, np.ndarray]:
        if self._matrix is None or self._rowids is None:
            rows = self.conn.execute(
                "SELECT chunk_rowid, embedding FROM vectors ORDER BY chunk_rowid"
            ).fetchall()
            if not rows:
                self._matrix = np.zeros((0, self.dim), dtype=np.float32)
                self._rowids = np.zeros((0,), dtype=np.int64)
            else:
                self._matrix = np.vstack(
                    [np.frombuffer(r["embedding"], dtype=np.float32) for r in rows]
                )
                self._rowids = np.array([r["chunk_rowid"] for r in rows], dtype=np.int64)
        return self._matrix, self._rowids

    def search(
        self, query: np.ndarray, k: int, filters: Filters | None = None
    ) -> list[Hit]:
        """Top-k by cosine similarity, with metadata filters applied."""
        filters = filters or Filters()
        query = np.ascontiguousarray(query.astype(np.float32).reshape(-1))
        if query.shape[0] != self.dim:
            raise EmbedderMismatchError(
                f"query dimension {query.shape[0]} does not match store dim {self.dim}"
            )
        where, params = filters.sql()

        if self._vec_ok:
            # Oversample, because vec0 k-NN runs before the metadata filter.
            oversample = max(k * 8, 64)
            knn = self.conn.execute(
                "SELECT chunk_rowid, distance FROM vec_chunks "
                "WHERE embedding MATCH ? AND k = ?",
                (query.tobytes(), oversample),
            ).fetchall()
            if knn:
                scores = {r["chunk_rowid"]: 1.0 - float(r["distance"]) for r in knn}
                marks = ", ".join("?" for _ in scores)
                rows = self.conn.execute(
                    f"SELECT rowid, * FROM chunks WHERE rowid IN ({marks}) AND {where}",
                    list(scores.keys()) + params,
                ).fetchall()
                hits = [self._to_hit(r, scores[r["rowid"]]) for r in rows]
                hits.sort(key=lambda h: h.score, reverse=True)
                if len(hits) >= k or len(knn) < oversample:
                    return hits[:k]
                # The filter removed too much of the oversampled window. Fall through
                # to the exhaustive path rather than return a truncated result set.

        matrix, rowids = self._load_matrix()
        if matrix.shape[0] == 0:
            return []
        allowed = self.conn.execute(
            f"SELECT rowid FROM chunks WHERE {where}", params
        ).fetchall()
        allowed_ids = {r["rowid"] for r in allowed}
        if not allowed_ids:
            return []
        mask = np.array([rid in allowed_ids for rid in rowids])
        sims = matrix[mask] @ query
        masked_rowids = rowids[mask]
        if sims.size == 0:
            return []
        top = np.argsort(-sims)[:k]
        selected = [(int(masked_rowids[i]), float(sims[i])) for i in top]
        marks = ", ".join("?" for _ in selected)
        rows = self.conn.execute(
            f"SELECT rowid, * FROM chunks WHERE rowid IN ({marks})",
            [rid for rid, _ in selected],
        ).fetchall()
        by_rowid = {r["rowid"]: r for r in rows}
        return [self._to_hit(by_rowid[rid], score) for rid, score in selected]

    @staticmethod
    def _to_hit(row: sqlite3.Row, score: float) -> Hit:
        return Hit(
            chunk_id=row["chunk_id"],
            text=row["text"],
            score=score,
            source=row["source"],
            publisher=row["publisher"],
            refresh_date=row["refresh_date"],
            crop=row["crop"],
            region=row["region"],
            season=row["season"],
            topic=row["topic"],
            lang=row["lang"],
            anchor=row["anchor"],
            doc_id=row["doc_id"],
            placeholder=bool(row["placeholder"]),
            validated=bool(row["validated"]),
        )
