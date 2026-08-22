#!/usr/bin/env python3
"""BUILD TIME. Download the sentence embedder into models/embedder/.

NETWORK ACCESS: yes, and only here. This runs on a developer machine before the index is
built. Nothing under src/mhizha/{rag,llm,app,i18n} may reach the network, and
tests/test_offline.py proves it by static import scan.

WHY THIS EXISTS
---------------
`make setup` used to install Python dependencies and stop, so a fresh clone had no embedder
weights. `load_embedder` then quietly fell back to a deterministic hash embedder, and every
retrieval result differed from ours while looking perfectly normal.

That is worse than a crash. A judge reproducing docs/SCREENSHOTS.md would have got different
passages, different scores and a different answer, with nothing on screen to explain why,
and the reasonable conclusion from their side is that our captures were fabricated. A
silent fallback that changes results is indistinguishable from dishonesty at a distance.

So the weights are fetched here, `allow_hash_fallback` defaults to false, and the hash
embedder is now something a developer opts into rather than something a stranger receives.
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from mhizha.config import load_config  # noqa: E402


def main() -> int:
    cfg = load_config().embedder
    target = cfg.path if cfg.path.is_absolute() else REPO / cfg.path

    if target.is_dir() and any(target.iterdir()):
        print(f"embedder already present at {target.relative_to(REPO)} - skipping")
        return 0

    try:
        from sentence_transformers import SentenceTransformer
    except ImportError:
        print("error: sentence-transformers is not installed. Run `make setup` first, or\n"
              "       pip install -r requirements.txt", file=sys.stderr)
        return 2

    print(f"downloading {cfg.id} into {target.relative_to(REPO)} (~{cfg.est_size_mb} MB)")
    target.parent.mkdir(parents=True, exist_ok=True)
    model = SentenceTransformer(cfg.id)
    model.save(str(target))

    dim = model.get_sentence_embedding_dimension()
    if dim != cfg.dim:
        print(f"error: {cfg.id} produces {dim}-dim vectors, config declares {cfg.dim}.\n"
              f"       The index schema and the config must agree before building.",
              file=sys.stderr)
        return 1
    print(f"done: {target.relative_to(REPO)} ({dim} dimensions)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
