"""RUNTIME (offline). Retrieval and confidence scoring.

## The confidence score

This number is a safety mechanism, not a UI decoration. It is the only thing standing
between a farmer and a fluent, well-cited, wrong answer. Tuning it upward to make a demo
answer more questions is the single most damaging change anyone can make here.

    confidence = 0.60 * top1
               + 0.25 * margin_term
               + 0.15 * agreement_term

  top1            cosine similarity of the best passage. Is anything relevant at all?
  margin_term     (top1 - mean(rest)) scaled by `min_margin`, clamped to [0, 1]. A high
                  top1 with an equally high tail means the corpus cannot distinguish
                  this question from its neighbours, which is exactly when a model
                  confabulates a blend of them.
  agreement_term  fraction of retrieved passages within 0.10 of top1 that come from a
                  DIFFERENT document than the top passage. Two near-identical chunks of
                  one document are one source stated twice, not corroboration.

Calibrate against eval/, never by intuition. If you move `abstain_below`, re-run
`make eval` and report abstention precision and recall with the change.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace

import numpy as np

from ..config import Config
from .embedder import Embedder
from .store import Filters, Hit, VectorStore

AGREEMENT_WINDOW = 0.10

# Region names as a farmer writes them, mapped to corpus region values.
#
# Region is metadata, not similarity: a Matabeleland North question must not be answered
# from a Mashonaland Central passage no matter how well the two embed together. This is
# the near-miss that matters most, because the provinces differ enough that one region's
# planting calendar is actively wrong advice in another.
#
# District-level names are NOT mapped yet (gap G-13). A farmer naming their district
# rather than their province gets no region filter, which is the safe direction: no
# filter means no false exclusion.
REGION_ALIASES: dict[str, tuple[str, ...]] = {
    "mashonaland central": ("mashonaland-central",),
    "mashonaland east": ("mashonaland-east",),
    "mashonaland west": ("mashonaland-west",),
    "mashonaland": ("mashonaland-central", "mashonaland-east", "mashonaland-west"),
    "matabeleland north": ("matabeleland-north",),
    "matabeleland south": ("matabeleland-south",),
    "matabeleland": ("matabeleland-north", "matabeleland-south"),
    "manicaland": ("manicaland",),
    "masvingo": ("masvingo",),
    "midlands": ("midlands",),
    "harare": ("harare",),
    "bulawayo": ("bulawayo",),
}


def detect_regions(query: str) -> tuple[str, ...]:
    """Region values named in a query. Empty when none is named, which applies no filter."""
    lowered = query.lower().replace("-", " ")
    matched: list[str] = []
    consumed: list[str] = []
    for alias in sorted(REGION_ALIASES, key=len, reverse=True):
        if alias not in lowered:
            continue
        # Skip the broad alias when a more specific one already matched:
        # "Mashonaland Central" must not also pull in East and West.
        if any(alias in seen for seen in consumed):
            continue
        consumed.append(alias)
        matched.extend(REGION_ALIASES[alias])
    return tuple(dict.fromkeys(matched))

W_TOP1 = 0.60
W_MARGIN = 0.25
W_AGREEMENT = 0.15


@dataclass
class Confidence:
    score: float
    band: str  # high | medium | low
    top1: float
    margin: float
    agreement: float
    reason: str = ""

    @property
    def is_abstain(self) -> bool:
        return self.band == "low"


@dataclass
class RetrievalResult:
    query: str
    hits: list[Hit]
    confidence: Confidence
    filters_used: Filters = field(default_factory=Filters)

    @property
    def should_abstain(self) -> bool:
        return not self.hits or self.confidence.is_abstain


def score_confidence(hits: list[Hit], cfg: Config) -> Confidence:
    """Composite confidence over a retrieved set. See the module docstring."""
    if not hits:
        return Confidence(
            score=0.0, band="low", top1=0.0, margin=0.0, agreement=0.0,
            reason="no passages retrieved",
        )

    scores = np.array([h.score for h in hits], dtype=np.float64)
    top1 = float(scores[0])

    if len(scores) > 1:
        raw_margin = top1 - float(scores[1:].mean())
        denom = max(cfg.retrieval.min_margin * 4.0, 1e-6)
        margin_term = float(np.clip(raw_margin / denom, 0.0, 1.0))
    else:
        raw_margin = 0.0
        # A single hit gives no evidence either way. Neutral, not free credit.
        margin_term = 0.5

    near_top = [h for h in hits if top1 - h.score <= AGREEMENT_WINDOW]
    if len(near_top) > 1:
        best = hits[0]
        # Corroboration means a DIFFERENT document agreeing. Two near-identical chunks
        # from the same document are one source stated twice, and counting them as
        # agreement inflates confidence exactly where a long document repeats itself.
        corroborating = sum(1 for h in near_top[1:] if h.doc_id != best.doc_id)
        agreement_term = corroborating / (len(near_top) - 1)
    else:
        agreement_term = 0.0

    score = W_TOP1 * max(top1, 0.0) + W_MARGIN * margin_term + W_AGREEMENT * agreement_term
    score = float(np.clip(score, 0.0, 1.0))

    if score >= cfg.retrieval.band_high:
        band = "high"
    elif score >= cfg.retrieval.band_medium:
        band = "medium"
    elif score >= cfg.retrieval.abstain_below:
        band = "medium"
    else:
        band = "low"

    reason = ""
    if band == "low":
        if top1 < 0.3:
            reason = "no passage in the corpus is close to this question"
        elif raw_margin < cfg.retrieval.min_margin:
            reason = "retrieved passages are undifferentiated, the corpus cannot tell this question from its neighbours"
        else:
            reason = "retrieval confidence is below the abstention threshold"

    return Confidence(
        score=score,
        band=band,
        top1=top1,
        margin=float(raw_margin),
        agreement=float(agreement_term),
        reason=reason,
    )


def retrieve(
    query: str,
    store: VectorStore,
    embedder: Embedder,
    cfg: Config,
    *,
    filters: Filters | None = None,
    top_k: int | None = None,
) -> RetrievalResult:
    """Embed the query, fetch top-k with filters, and score confidence.

    Passages always come back with full provenance attached. This function never
    returns a bare string.
    """
    if filters is None:
        filters = Filters(
            validated_only=cfg.retrieval.validated_only,
            allow_placeholder=cfg.retrieval.allow_placeholder,
        )
    # A region named in the question is a hard constraint, applied unless the caller
    # already set one explicitly.
    if not filters.all_regions():
        detected = detect_regions(query)
        if detected:
            filters = replace(filters, regions=detected)
    k = top_k or cfg.retrieval.top_k
    vector = embedder.encode([query])[0]
    hits = store.search(vector, k, filters)
    confidence = score_confidence(hits, cfg)
    return RetrievalResult(
        query=query, hits=hits, confidence=confidence, filters_used=filters
    )
