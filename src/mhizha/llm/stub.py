"""RUNTIME (offline). Deterministic extractive backend.

Default in a fresh checkout, and the backend the test suite uses, so tests never depend
on a multi-gigabyte download and a safety property can be shown to hold independently of
which generator produced the text.

It extracts sentences from the retrieved passages by lexical overlap with the question
and cites them. It never writes a sentence that is not already in a passage, which makes
it a useful floor: anything the real model does worse than this is a regression.
"""

from __future__ import annotations

import re

from .base import GenerationRequest, GenerationResult
from .prompts import INSUFFICIENT, PASSAGE_PREFIX

_STOPWORDS = frozenset(
    """
    a an and are as at be by can do does for from how i in is it my of on or should
    that the their there they this to was what when where which who why will with you
    your me we us our if not no yes
    """.split()
)

_PASSAGE_BLOCK = re.compile(
    rf"\[({PASSAGE_PREFIX}\d+)\][^\n]*\n(.*?)(?=\n\n\[{PASSAGE_PREFIX}\d+\]|\n\nQUESTION:)",
    re.DOTALL,
)
_QUESTION = re.compile(r"^QUESTION:\s*(.+?)$", re.MULTILINE)
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")
_PARAGRAPH_SPLIT = re.compile(r"\n\s*\n")


def _tokens(text: str) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9]+", text.lower()) if t not in _STOPWORDS}


def _sentences(body: str) -> list[str]:
    """Reflow wrapped lines before splitting, so a sentence is not cut at a line break."""
    out: list[str] = []
    for paragraph in _PARAGRAPH_SPLIT.split(body):
        reflowed = re.sub(r"\s*\n\s*", " ", paragraph).strip()
        if not reflowed:
            continue
        # A markdown heading or a table row is not a sentence and reads badly quoted.
        if reflowed.startswith("#") or reflowed.startswith("|"):
            continue
        out.extend(s.strip() for s in _SENTENCE_SPLIT.split(reflowed) if s.strip())
    return out


class StubBackend:
    """Extractive, deterministic, no weights."""

    name = "stub"
    model_id = "stub-extractive-v1"

    def __init__(self, max_sentences: int = 3) -> None:
        self.max_sentences = max_sentences

    def resident_mb(self) -> float:
        return 0.0

    def generate(self, request: GenerationRequest) -> GenerationResult:
        passages = _PASSAGE_BLOCK.findall(request.prompt)
        question_match = _QUESTION.search(request.prompt)
        question = question_match.group(1) if question_match else ""
        q_tokens = _tokens(question)

        scored: list[tuple[float, str, str]] = []
        for pid, body in passages:
            for sentence in _sentences(body):
                if len(sentence) < 25:
                    continue
                s_tokens = _tokens(sentence)
                if not s_tokens:
                    continue
                overlap = len(q_tokens & s_tokens)
                if overlap == 0:
                    continue
                # Normalise by sentence length so a long sentence does not win on
                # incidental word matches alone.
                score = overlap / (len(s_tokens) ** 0.5)
                scored.append((score, sentence, pid))

        if not scored:
            return GenerationResult(
                text=INSUFFICIENT, backend=self.name, model_id=self.model_id,
                prompt_tokens=len(request.prompt) // 4, output_tokens=2,
            )

        scored.sort(key=lambda t: (-t[0], t[2], t[1]))
        chosen: list[tuple[str, str]] = []
        seen: set[str] = set()
        for _, sentence, pid in scored:
            key = sentence[:60].lower()
            if key in seen:
                continue
            seen.add(key)
            chosen.append((sentence, pid))
            if len(chosen) >= self.max_sentences:
                break

        text = " ".join(
            f"{s.rstrip('.')}. [{pid}]" for s, pid in chosen
        )
        return GenerationResult(
            text=text, backend=self.name, model_id=self.model_id,
            prompt_tokens=len(request.prompt) // 4, output_tokens=len(text) // 4,
        )
