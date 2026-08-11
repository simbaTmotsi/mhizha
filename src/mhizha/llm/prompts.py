"""RUNTIME (offline). Grounded prompt construction.

Two properties matter more than wording here:

1. The context block contains retrieved passages and nothing else, each with a short id.
   Citations come back as those ids, so grounding can be verified mechanically in
   app/safety.py rather than trusted.
2. The prompt stays short. On a 1B model every token of preamble competes with the
   passages themselves for both attention and KV cache, and the KV cache is a line item
   in the device budget.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..rag.store import Hit

PASSAGE_PREFIX = "P"

_SYSTEM = {
    "en": (
        "You are Mhizha, an agronomy assistant for smallholder farmers in Zimbabwe.\n"
        "Answer ONLY from the numbered passages provided. Never use outside knowledge.\n"
        "Cite every claim with its passage id, like [P1].\n"
        "If the passages do not answer the question, reply exactly: INSUFFICIENT_CONTEXT\n"
        "Never state a chemical dosage, mixing rate, or spray interval unless the exact "
        "figure appears in a passage. Do not estimate, round, or generalise a figure.\n"
        "Be brief and practical. Write for a farmer, not an agronomist."
    ),
    "sn": (
        "You are Mhizha, an agronomy assistant for smallholder farmers in Zimbabwe.\n"
        "Answer ONLY from the numbered passages provided. Never use outside knowledge.\n"
        "Cite every claim with its passage id, like [P1].\n"
        "If the passages do not answer the question, reply exactly: INSUFFICIENT_CONTEXT\n"
        "Never state a chemical dosage, mixing rate, or spray interval unless the exact "
        "figure appears in a passage.\n"
        "Write your answer in Shona. Keep source titles in their original language.\n"
        "Be brief and practical."
    ),
    "nd": (
        "You are Mhizha, an agronomy assistant for smallholder farmers in Zimbabwe.\n"
        "Answer ONLY from the numbered passages provided. Never use outside knowledge.\n"
        "Cite every claim with its passage id, like [P1].\n"
        "If the passages do not answer the question, reply exactly: INSUFFICIENT_CONTEXT\n"
        "Never state a chemical dosage, mixing rate, or spray interval unless the exact "
        "figure appears in a passage.\n"
        "Write your answer in Ndebele. Keep source titles in their original language.\n"
        "Be brief and practical."
    ),
}

INSUFFICIENT = "INSUFFICIENT_CONTEXT"


@dataclass
class GroundedPrompt:
    system: str
    prompt: str
    passage_map: dict[str, Hit]  # "P1" -> Hit

    def chunk_id_for(self, passage_id: str) -> str | None:
        hit = self.passage_map.get(passage_id)
        return hit.chunk_id if hit else None


def build_prompt(question: str, hits: list[Hit], lang: str = "en") -> GroundedPrompt:
    """Compose the grounded prompt. Passage ids in, citation ids out."""
    system = _SYSTEM.get(lang, _SYSTEM["en"])
    passage_map: dict[str, Hit] = {}
    blocks: list[str] = []
    for i, hit in enumerate(hits, start=1):
        pid = f"{PASSAGE_PREFIX}{i}"
        passage_map[pid] = hit
        # Metadata line is part of the passage so the model can qualify by region and
        # season rather than flattening a regional recommendation into a national one.
        meta = f"crop={hit.crop} region={hit.region} season={hit.season}"
        blocks.append(f"[{pid}] ({meta})\n{hit.text.strip()}")

    context = "\n\n".join(blocks)
    prompt = (
        f"PASSAGES:\n{context}\n\n"
        f"QUESTION: {question.strip()}\n\n"
        f"ANSWER (cite passage ids, or reply {INSUFFICIENT}):"
    )
    return GroundedPrompt(system=system, prompt=prompt, passage_map=passage_map)


def estimate_tokens(text: str) -> int:
    """Rough token estimate. Deliberately crude: it feeds a budget warning, not billing."""
    return max(1, len(text) // 4)
