"""RUNTIME (offline). The answer path, readable top to bottom.

question -> normalise -> retrieve -> confidence gate -> ground -> generate -> safety ->
response

The confidence gate sits before generation on purpose. Below the threshold the model is
not called at all, because a model handed weak context still produces fluent prose, and
fluent prose about a planting date is indistinguishable from knowledge to the person
reading it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..config import Config
from ..i18n import Translator
from ..llm.base import GenerationRequest, LLMBackend
from ..llm.prompts import INSUFFICIENT, build_prompt
from ..rag.embedder import Embedder
from ..rag.retrieve import Confidence, retrieve
from ..rag.store import Filters, Hit, VectorStore
from . import safety


@dataclass
class Source:
    chunk_id: str
    passage_id: str
    title: str
    publisher: str
    refresh_date: str
    anchor: str
    score: float
    validated: bool
    placeholder: bool

    def line(self) -> str:
        flags = []
        if self.placeholder:
            flags.append("PLACEHOLDER")
        if not self.validated:
            flags.append("unvalidated")
        suffix = f" [{', '.join(flags)}]" if flags else ""
        return (
            f"{self.title} ({self.publisher}, refreshed {self.refresh_date})"
            f" {self.anchor}{suffix}"
        )


@dataclass
class Answer:
    """The response contract. The CLI and any future Android UI render this same object."""

    question: str
    lang: str
    answer_text: str
    sources: list[Source]
    confidence: Confidence
    abstained: bool
    abstain_reason: str = ""
    notices: list[str] = field(default_factory=list)
    fallback_from: list[str] = field(default_factory=list)
    backend: str = ""
    model_id: str = ""
    safety_findings: list[safety.Finding] = field(default_factory=list)
    trace: dict[str, Any] = field(default_factory=dict)

    @property
    def confidence_band(self) -> str:
        return self.confidence.band

    def to_dict(self) -> dict[str, Any]:
        return {
            "question": self.question,
            "lang": self.lang,
            "answer": self.answer_text,
            "abstained": self.abstained,
            "abstain_reason": self.abstain_reason,
            "confidence": {
                "score": round(self.confidence.score, 4),
                "band": self.confidence.band,
                "top1": round(self.confidence.top1, 4),
                "margin": round(self.confidence.margin, 4),
                "agreement": round(self.confidence.agreement, 4),
            },
            "sources": [
                {
                    "passage_id": s.passage_id,
                    "chunk_id": s.chunk_id,
                    "title": s.title,
                    "publisher": s.publisher,
                    "refresh_date": s.refresh_date,
                    "anchor": s.anchor,
                    "score": round(s.score, 4),
                    "validated": s.validated,
                    "placeholder": s.placeholder,
                }
                for s in self.sources
            ],
            "notices": self.notices,
            "fallback_from": self.fallback_from,
            "backend": self.backend,
            "model_id": self.model_id,
            "safety_findings": [
                {"rule": f.rule, "severity": f.severity, "detail": f.detail}
                for f in self.safety_findings
            ],
        }


def _sources_from(hits: list[Hit], cited: list[str] | None = None) -> list[Source]:
    sources: list[Source] = []
    for i, hit in enumerate(hits, start=1):
        pid = f"P{i}"
        if cited is not None and pid not in cited:
            continue
        sources.append(
            Source(
                chunk_id=hit.chunk_id,
                passage_id=pid,
                title=hit.source,
                publisher=hit.publisher,
                refresh_date=hit.refresh_date,
                anchor=hit.anchor,
                score=hit.score,
                validated=hit.validated,
                placeholder=hit.placeholder,
            )
        )
    return sources


def _clarifying_question(hits: list[Hit], tr: Translator) -> str:
    """Ask for the one missing detail most likely to unblock retrieval.

    Region first: Zimbabwe's agro-ecological regions differ enough that a national answer
    is often the wrong answer, and region is also the detail farmers most often omit.
    """
    regions = {h.region for h in hits}
    crops = {h.crop for h in hits}
    if len(regions) > 1 or not hits:
        ask = tr.t("abstain.clarify_region")
    elif len(crops) > 1:
        ask = tr.t("abstain.clarify_crop")
    else:
        ask = tr.t("abstain.clarify_season")
    return f"{tr.t('abstain.clarify_prefix')} {ask}?"


def answer_question(
    question: str,
    *,
    cfg: Config,
    store: VectorStore,
    embedder: Embedder,
    backend: LLMBackend,
    lang: str | None = None,
    filters: Filters | None = None,
) -> Answer:
    """The whole path. No network call anywhere in this function or below it."""
    lang = lang or cfg.i18n.default_lang
    tr = Translator(cfg.i18n.locales_dir, lang, cfg.i18n.default_lang)

    # 1. Retrieve.
    result = retrieve(question, store, embedder, cfg, filters=filters)

    # 2. Corpus text is data, never instruction.
    hits, injection_findings = safety.scan_passages_for_injection(result.hits)
    if injection_findings:
        from ..rag.retrieve import score_confidence

        result.confidence = score_confidence(hits, cfg)

    def abstain(reason_key: str, reason_detail: str,
                clarify_it: bool = True) -> Answer:
        body = tr.t(reason_key)
        clarify = _clarifying_question(hits, tr) if clarify_it else tr.t(
            "safety.agrochemical_notice"
        )
        referral = tr.t("abstain.referral")
        notices = ["safety.injection_dropped"] if injection_findings else []
        return Answer(
            question=question,
            lang=lang,
            answer_text=f"{body}\n\n{clarify}\n\n{referral}",
            sources=_sources_from(hits),
            confidence=result.confidence,
            abstained=True,
            abstain_reason=reason_detail,
            notices=notices,
            fallback_from=list(tr.fallbacks),
            backend=backend.name,
            model_id=backend.model_id,
            safety_findings=injection_findings,
            trace={"stage": "pre-generation", "hits": len(hits)},
        )

    # 3. Confidence gate. Below the threshold the model is never called.
    if not hits:
        return abstain("abstain.no_context", "no passages retrieved")
    if result.confidence.is_abstain:
        return abstain("abstain.low_confidence", result.confidence.reason)

    # 4. R5 quantity-intent gate, also before generation. If the question asks for a
    # figure and no validated passage holds one, no possible generation is groundable,
    # so refuse rather than let the model summarise its way around the question.
    intent = safety.quantity_intent(question, cfg.safety)
    if intent and not safety.has_groundable_quantity(hits, cfg.safety):
        return abstain("safety.dosage_withheld", f"R5: {intent}", clarify_it=False)

    # 5. Ground.
    grounded = build_prompt(question, hits, lang)

    # 6. Generate.
    generation = backend.generate(
        GenerationRequest(
            system=grounded.system,
            prompt=grounded.prompt,
            max_tokens=cfg.llm.max_output_tokens,
            temperature=cfg.llm.temperature,
            seed=cfg.llm.seed,
            stop=("QUESTION:", "PASSAGES:"),
        )
    )

    if INSUFFICIENT in generation.text or not generation.text.strip():
        return abstain("abstain.no_context", "model reported insufficient context")

    # 7. Safety. The only path to a displayable answer.
    outcome = safety.check(
        generation.text,
        hits,
        cfg.safety,
        validated_only=cfg.retrieval.validated_only,
    )
    findings = injection_findings + outcome.findings

    if not outcome.allowed:
        body = tr.t(outcome.withheld_reason)
        referral = tr.t("abstain.referral")
        return Answer(
            question=question,
            lang=lang,
            answer_text=f"{body}\n\n{referral}",
            sources=_sources_from(hits),
            confidence=result.confidence,
            abstained=True,
            abstain_reason="withheld by safety: "
            + "; ".join(f.detail for f in outcome.critical),
            notices=outcome.notices,
            fallback_from=list(tr.fallbacks),
            backend=generation.backend,
            model_id=generation.model_id,
            safety_findings=findings,
            trace={"stage": "post-generation", "raw": generation.text},
        )

    # 8. Assemble. Sources are never optional and never truncated.
    notices = [tr.t(key) for key in outcome.notices]
    return Answer(
        question=question,
        lang=lang,
        answer_text=outcome.text,
        sources=_sources_from(hits, outcome.cited_passages),
        confidence=result.confidence,
        abstained=False,
        notices=notices,
        fallback_from=list(tr.fallbacks),
        backend=generation.backend,
        model_id=generation.model_id,
        safety_findings=findings,
        trace={
            "stage": "answered",
            "prompt_tokens": generation.prompt_tokens,
            "output_tokens": generation.output_tokens,
            "retrieved": len(hits),
            "cited": outcome.cited_passages,
        },
    )
