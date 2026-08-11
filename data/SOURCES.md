# Mhizha corpus gap register

Every gap between what Mhizha should be able to answer and what its corpus actually
contains. This file is the reason the assistant can abstain honestly instead of guessing.

**Nothing in `data/corpus/` is real agronomic content today.** All four documents there
are structural placeholders carrying `placeholder: true`, and they state no dates, no
rates, no thresholds, and no product names.

Status values: `UNSOURCED` (identified, nothing obtained) → `REQUESTED` (asked, waiting)
→ `RECEIVED` (have the document, not yet ingested) → `INGESTED` (in the corpus, still
needs human validation) → `VALIDATED` (signed off in `data/review_ledger.jsonl`).

---

## Gaps

| ID | What is missing | Blocks | Likely holder | Status |
|---|---|---|---|---|
| G-01 | Maize planting calendars by agro-ecological region, tied to onset of effective rains | Planting calendar questions, the highest-volume expected query class | AGRITEX; Seed Co and Pannar variety guides; CIMMYT Zimbabwe | UNSOURCED |
| G-02 | Variety maturity classes and their regional suitability (maize, sorghum, millet, groundnut, soya, cowpea) | Crop and variety selection | Seed Co, Pannar, Zimbabwe Seed Association; DR&SS | UNSOURCED |
| G-03 | Pest and disease identification sheets: local names, field-visible symptoms, look-alikes, economic thresholds, non-chemical options first | Pest and disease questions, the highest-risk category | Plant Protection Research Institute; FAO Zimbabwe fall armyworm material; CABI Plantwise | UNSOURCED |
| G-04 | Fertiliser recommendations by crop and soil type, with basal and top dressing rates and timing | Soil and fertiliser questions | AGRITEX; Chemistry and Soil Research Institute; university extension | UNSOURCED |
| G-05 | Post-harvest: maturity indicators, safe storage moisture, drying methods, storage pest management, registered treatments with withholding periods | Post-harvest questions | AGRITEX; FAO post-harvest programme | UNSOURCED |
| G-06 | Registered agrochemical list for Zimbabwe with current label rates, pre-harvest intervals, and re-entry periods; plus the banned and restricted list | Every agrochemical question. Until this exists Mhizha must refuse all rate questions | Plant Protection Research Institute; Pesticides and Toxic Substances registrar | UNSOURCED |
| G-07 | Irrigation and water: scheduling for smallholder plots, rainwater harvesting, conservation agriculture moisture practice | Water and irrigation questions | AGRITEX; ICRISAT; conservation agriculture programmes | UNSOURCED |
| G-08 | Expert review of the agrochemical trigger term list in `config.yaml: safety.trigger_terms` | Safety guard coverage. The current list is a first pass by a non-agronomist and is certainly incomplete | Agronomist or extension specialist | UNSOURCED |
| G-09 | Measured on-device memory and latency figures for each model in `llm/registry.py`, on a representative 4 GB Zimbabwean handset | Model selection. Every size figure in the registry is currently an estimate marked `(approx, unverified)` | Us, with a test device | UNSOURCED |
| G-10 | Shona and Ndebele translations of all user-facing strings, safety copy first | Local language support. Every value in `sn.yaml` and `nd.yaml` is `TODO_TRANSLATE` | Fluent speakers with agricultural extension familiarity | UNSOURCED |
| G-11 | Shona and Ndebele agronomic term list for query-side mapping (pest names, crop stages, soil terms) | Cross-language retrieval against an English corpus | Extension officers; university language and agriculture departments | UNSOURCED |
| G-12 | A multilingual embedding model choice, sized against the 4 GB budget | Cross-language retrieval. The current embedder is English-only | Us, benchmarking | UNSOURCED |
| G-13 | District to province mapping for Zimbabwe | Region filtering. `rag/retrieve.py: REGION_ALIASES` maps provinces only, so a farmer naming their district gets no region filter. That fails safe (no filter, no false exclusion) but it also means the region near-miss guard does not protect them | ZimStats; AGRITEX district structure | UNSOURCED |
| G-14 | Retrieval threshold calibration against real validated content | `retrieval.abstain_below` is currently an uncalibrated default of 0.45. Measured on the placeholder corpus, answerable and unanswerable questions overlap in similarity (an answerable case scores 0.463 while an out-of-corpus crop scores 0.487), so no threshold separates them. Calibration is meaningless until G-01 through G-07 land | Us, once real content exists | BLOCKED on G-01..G-07 |

---

## Rules for filling a gap

1. **Do not author agronomic content.** Not to fill a gap, not to make a demo work, not
   as a temporary measure. A plausible invented fact in this corpus becomes a wrong
   answer delivered to a farmer with a citation attached, which is worse than silence.
2. **Capture provenance at ingest.** Title, publisher, and refresh date are required and
   ingestion fails without them. Provenance not captured at ingest cannot be recovered.
3. **Undated means quarantined.** Never default `refresh_date` to today and never infer
   it from file mtime. An undated planting calendar is a liability.
4. **Human validation is separate from ingestion.** Ingested content is `validated: false`
   until a named reviewer signs it off against its exact text hash.
5. **Permission matters.** Record the licence or permission under which each source is
   redistributable inside an app, in the notes column when the source arrives. Extension
   material is often freely usable, but that has to be checked rather than assumed.

## Sourcing notes

The organisations named above are the likely holders of this material. None have been
contacted yet, and none of this material has been obtained, so no assumption should be
made about availability, licensing, or currency. AGRITEX is the primary target: it is the
national extension service and its guidance is what an officer in the field would give.
