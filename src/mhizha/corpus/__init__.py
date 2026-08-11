"""BUILD TIME. Corpus ingestion, cleaning, chunking, and human review.

Nothing in this package runs on the farmer's device. Modules here may touch the network
(to fetch a source document) provided they say so explicitly and log it. Runtime code
under mhizha.rag, mhizha.llm, and mhizha.app may not import from here.
"""

from __future__ import annotations
