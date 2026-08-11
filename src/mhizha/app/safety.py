"""RUNTIME (offline). The single safety choke point.

Every generated answer passes through `check()` before it can be displayed. There is no
bypass flag, and adding one would defeat the purpose of having one choke point.

Four rules, each with tests in tests/test_safety.py:

  R1 citations exist and resolve   an answer with no valid passage citation is not an
                                   answer, it is unattributed text
  R2 no fabricated citation ids    citing [P9] when five passages were supplied is the
                                   system lying about its own evidence
  R3 agrochemical quantity guard   a dosage, rate, or interval must appear verbatim in a
                                   retrieved passage. Not approximated, not rounded, not
                                   "about". This is the rule that stops a fluent model
                                   destroying a season or poisoning someone
  R4 prompt injection in passages  corpus text is data, never instruction
  R5 quantity-intent gate          if the question ASKS for a rate, dose, interval, or
                                   restricted product and no validated passage holds
                                   such a figure, refuse before generating. R3 alone is
                                   not enough: it only inspects what the model wrote, so
                                   a model that summarises a chemical document without
                                   quoting a number passes R3 while still reading as
                                   advice on a question that deserved a refusal

R3 withholds the whole answer rather than redacting the number. A redacted answer still
reads as advice, and a farmer acting on the surrounding sentences without the figure is
no safer than one acting on a wrong figure.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from ..config import SafetyConfig
from ..rag.store import Hit

# A number, optionally a range, followed by a unit. Compiled per-config because the unit
# vocabulary lives in config.yaml.
_NUMBER = r"\d+(?:[.,]\d+)?"

_INJECTION_PATTERNS = (
    re.compile(r"\bignore (?:all |any )?(?:previous|prior|above) instructions?\b", re.I),
    re.compile(r"\bdisregard (?:the |your )?(?:system|previous|above)\b", re.I),
    re.compile(r"\byou are now\b.{0,40}\b(?:assistant|model|agent)\b", re.I),
    re.compile(r"\b(?:new|updated) (?:instructions?|system prompt)\s*[:\-]", re.I),
    re.compile(r"\bdo not cite\b|\bwithout citing\b", re.I),
    re.compile(r"\bsafety (?:rules?|checks?) (?:are |is )?(?:off|disabled)\b", re.I),
)

_CITATION = re.compile(r"\[(P\d+)\]")

# R5. Three families of question that must not be answered without a validated figure.
#
# (a) a direct request for a quantity
# (b) a request for a banned, restricted, or off-label product
# (c) an invitation to generalise: "the usual rate", "typical dates". Those adjectives
#     are precisely the request to go beyond a source, and a model will oblige.
_QUANTITY_INTENT = (
    re.compile(r"\bhow (?:much|many|long|often)\b", re.I),
    re.compile(r"\bwhat (?:rate|dose|dosage|amount|quantity|concentration|interval)\b", re.I),
    re.compile(r"\b(?:mixing|application|spray|dilution|seeding) rate\b", re.I),
    re.compile(r"\b(?:give|tell|show) (?:me|us)\b.{0,40}\b(?:rate|dose|dosage|amount|quantity)\b", re.I),
    re.compile(r"\brough(?:ly)?\s+(?:amount|idea|figure|estimate)\b", re.I),
    re.compile(r"\b(?:exact|precise|correct)\b.{0,30}\b(?:rate|dose|dosage|amount)\b", re.I),
)
_RESTRICTED_INTENT = (
    re.compile(r"\b(?:banned|restricted|illegal|unregistered|black ?market)\b", re.I),
    re.compile(r"\b(?:instead of|rather than)\b.{0,40}\b(?:label|registered|approved)\b", re.I),
)
_GENERALISE_INTENT = (
    re.compile(
        r"\b(?:usual|typical|standard|normal|average|common|general)\b"
        r".{0,30}\b(?:rate|rates|dose|dosage|amount|date|dates|window|interval|period)\b",
        re.I,
    ),
    re.compile(r"\b(?:guess|estimate|make up|approximate)\b", re.I),
    re.compile(r"\bwhat would you (?:use|recommend|apply)\b", re.I),
)


@dataclass
class Finding:
    rule: str
    severity: str  # critical | error | warning
    detail: str
    evidence: str = ""


@dataclass
class SafetyOutcome:
    allowed: bool
    text: str
    findings: list[Finding] = field(default_factory=list)
    cited_passages: list[str] = field(default_factory=list)
    notices: list[str] = field(default_factory=list)
    withheld_reason: str = ""

    @property
    def critical(self) -> list[Finding]:
        return [f for f in self.findings if f.severity == "critical"]


def _normalise_quantity(text: str) -> str:
    """Collapse the spacing and punctuation variants of the same figure.

    "50 ml", "50ml", and "50,0 ml" must all compare equal to a passage that writes any
    one of them, otherwise the verbatim check fails on formatting and we withhold a
    correctly-sourced figure.
    """
    text = text.lower().replace(",", ".")
    return re.sub(r"\s+", "", text)


def _quantity_regex(cfg: SafetyConfig) -> re.Pattern[str]:
    units = sorted((re.escape(u) for u in cfg.quantity_units), key=len, reverse=True)
    unit_alt = "|".join(units)
    # Trailing lookahead rather than \b: a unit like "%" is not a word character, so \b
    # after it never matches and the guard silently misses "5 %".
    # `s?` catches the plural a farmer or a document actually writes ("10 litres").
    return re.compile(
        rf"({_NUMBER}(?:\s*(?:-|to)\s*{_NUMBER})?)\s*"
        rf"(?:{unit_alt})s?(?:\s*/\s*(?:{unit_alt})s?)?(?![A-Za-z0-9])",
        re.IGNORECASE,
    )


def _near_trigger(text: str, start: int, end: int, cfg: SafetyConfig) -> str | None:
    lo = max(0, start - cfg.quantity_proximity_chars)
    hi = min(len(text), end + cfg.quantity_proximity_chars)
    window = text[lo:hi].lower()
    for term in cfg.trigger_terms:
        if term in window:
            return term
    return None


def quantity_intent(question: str, cfg: SafetyConfig) -> str | None:
    """R5. Does this question ask for a figure we must not invent? Returns the reason.

    Deliberately errs long. A false positive costs a farmer one refusal with a referral
    to their extension officer. A false negative costs them a chemical applied at a rate
    a machine made up.
    """
    if not cfg.agrochemical_guard:
        return None
    lowered = question.lower()
    has_trigger = any(term in lowered for term in cfg.trigger_terms)

    if has_trigger and any(p.search(question) for p in _QUANTITY_INTENT):
        return "question asks for a chemical or fertiliser quantity"
    if has_trigger and any(p.search(question) for p in _RESTRICTED_INTENT):
        return "question asks about a banned, restricted, or off-label product"
    if any(p.search(question) for p in _GENERALISE_INTENT):
        return "question invites a generalised figure rather than a sourced one"
    return None


def has_groundable_quantity(hits: list[Hit], cfg: SafetyConfig) -> bool:
    """Is there a validated, non-placeholder passage holding an actual figure?

    If not, no amount of generation can produce a groundable answer to a quantity
    question, so the model is never called.
    """
    pattern = _quantity_regex(cfg)
    for hit in hits:
        if not hit.validated or hit.placeholder:
            continue
        for match in pattern.finditer(hit.text):
            if _near_trigger(hit.text, match.start(), match.end(), cfg):
                return True
    return False


def scan_passages_for_injection(hits: list[Hit]) -> tuple[list[Hit], list[Finding]]:
    """R4. Drop passages that carry instruction-like text.

    Corpus text is data. A passage that tries to instruct the model is either a scraping
    accident or an attack, and neither belongs in a grounded prompt.
    """
    clean: list[Hit] = []
    findings: list[Finding] = []
    for hit in hits:
        matched = next(
            (p.pattern for p in _INJECTION_PATTERNS if p.search(hit.text)), None
        )
        if matched:
            findings.append(
                Finding(
                    rule="R4",
                    severity="error",
                    detail=f"passage {hit.chunk_id} contains instruction-like text and was dropped",
                    evidence=matched,
                )
            )
        else:
            clean.append(hit)
    return clean, findings


def check(
    answer_text: str,
    hits: list[Hit],
    cfg: SafetyConfig,
    *,
    validated_only: bool = False,
) -> SafetyOutcome:
    """Run every safety rule. This is the only path to a displayable answer.

    `validated_only` reflects the retrieval profile. R3 is stricter than it and does not
    consult it: a quantity always needs a validated, non-placeholder source.
    """
    findings: list[Finding] = []
    notices: list[str] = []

    passage_ids = {f"P{i}" for i in range(1, len(hits) + 1)}
    by_pid = {f"P{i}": hit for i, hit in enumerate(hits, start=1)}
    cited = _CITATION.findall(answer_text)

    # R2 first: a fabricated id must not be counted as a valid citation by R1.
    fabricated = sorted({c for c in cited if c not in passage_ids})
    if fabricated:
        findings.append(
            Finding(
                rule="R2",
                severity="critical",
                detail=f"answer cites passage ids that were never supplied: {', '.join(fabricated)}",
                evidence=answer_text[:200],
            )
        )

    valid_cited = sorted({c for c in cited if c in passage_ids},
                         key=lambda p: int(p[1:]))

    # R1
    if cfg.require_citations and not valid_cited:
        findings.append(
            Finding(
                rule="R1",
                severity="critical",
                detail="answer contains no citation resolving to a retrieved passage",
                evidence=answer_text[:200],
            )
        )

    # R3
    if cfg.agrochemical_guard:
        # Only a cited, human-validated, non-placeholder passage may ground a quantity.
        #
        # This is stricter than retrieval.validated_only on purpose, and independent of
        # it. Unvalidated content is acceptable to summarise and can be shown to the
        # farmer with its provenance and an "unvalidated" flag. It is not acceptable as
        # the authority for a spray rate, because nobody has yet taken responsibility
        # for that number. A placeholder passage never grounds anything.
        allowed_hits = [
            h for h in (by_pid[p] for p in valid_cited)
            if h.validated and not h.placeholder
        ]
        haystack = _normalise_quantity(" ".join(h.text for h in allowed_hits))
        pattern = _quantity_regex(cfg)
        for match in pattern.finditer(answer_text):
            term = _near_trigger(answer_text, match.start(), match.end(), cfg)
            if term is None:
                continue
            quantity = _normalise_quantity(match.group(0))
            if quantity not in haystack:
                findings.append(
                    Finding(
                        rule="R3",
                        severity="critical",
                        detail=(
                            f"quantity {match.group(0).strip()!r} appears near the term "
                            f"{term!r} but is not verbatim in any cited validated passage"
                        ),
                        evidence=answer_text[
                            max(0, match.start() - 60): match.end() + 60
                        ],
                    )
                )
            else:
                if "safety.agrochemical_notice" not in notices:
                    notices.append("safety.agrochemical_notice")
                    notices.append("safety.extension_referral")

    # Any chemical term at all earns the notice, even with no figure attached.
    if cfg.agrochemical_guard and "safety.agrochemical_notice" not in notices:
        lowered = answer_text.lower()
        if any(t in lowered for t in cfg.trigger_terms):
            notices.append("safety.agrochemical_notice")
            notices.append("safety.extension_referral")

    critical = [f for f in findings if f.severity == "critical"]
    if critical:
        reason = "safety.dosage_withheld" if any(
            f.rule == "R3" for f in critical
        ) else "answer.no_sources"
        return SafetyOutcome(
            allowed=False,
            text="",
            findings=findings,
            cited_passages=valid_cited,
            notices=notices,
            withheld_reason=reason,
        )

    if any(by_pid[p].placeholder for p in valid_cited):
        notices.insert(0, "placeholder.warning")

    return SafetyOutcome(
        allowed=True,
        text=answer_text,
        findings=findings,
        cited_passages=valid_cited,
        notices=notices,
    )
