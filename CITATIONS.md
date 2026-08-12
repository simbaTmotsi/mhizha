# Citations and attributions

Everything this submission stands on that we did not write. Where a licence claim was read
out of a file in this repository or out of a model card we retrieved, it is marked
**retrieved** with the date. Where it is stated from general knowledge and has **not** been
re-verified against the upstream card, it is marked **unverified**, and it should be
checked before the licence text of any redistributed artefact is relied on.

The distinction matters here for one reason: this project has already been wrong about a
model licence once (Gemma 4 E2B was recorded as carrying the Gemma Terms of Use, carried
over from Gemma 2 and 3; it is Apache-2.0). That correction is registered as SR-04 in
`competition/superseded.yaml`.

---

## 1. Competition artefacts

Both vendored read-only under `vendor/` at the commits below. Nothing in `src/mhizha/`
imports from either. (**retrieved**, 11 Aug 2026, COMPETITION.md section 1.)

| Artefact | Commit | Licence |
|---|---|---|
| `Africa-Deep-Tech-Foundation/adtc-2026-submission-template` | `63ddc5422404f8ee112fc74d28e29764acd40a50` | GNU GPL v3 |
| `Africa-Deep-Tech-Foundation/adtc-profiler` | `7adbe08f157e9b96a670426339aca2a519706bdc` | GNU GPL v3 |

This repository is licensed **GPL-3.0** (`LICENSE`), which is compatible with, and chosen
because of, the licence of the organisers' template.

`competition/Dockerfile.native` is a derivative of `vendor/adtc-profiler/Dockerfile`:
identical to it, pinned to the same llama.cpp ref, differing only in the `GGML_AVX`,
`GGML_AVX2`, `GGML_FMA` and `GGML_F16C` flags. It exists to quantify the cost of the
official image's SIMD-disabled build (REPORT.md section 4.3) and is never a submission
artefact.

## 2. Inference and evaluation stack

| Component | Version / ref | Licence | How established |
|---|---|---|---|
| `ggerganov/llama.cpp` | `b10175` | MIT | ref **retrieved** from `vendor/adtc-profiler/Dockerfile:15`; licence **unverified** |
| `llama-cpp-python` | as pinned by the profiler image | MIT | **retrieved** as a dependency of the official image; licence **unverified** |
| `EleutherAI/lm-evaluation-harness` (`lm-eval>=0.4.4`) | as pinned by the profiler | MIT | pin **retrieved** from `vendor/adtc-profiler/pyproject.toml:20`; licence **unverified** |
| Docker | host-provided | Apache-2.0 | **unverified** |

The GGUF container format and the `llama-bench`, `llama-cli` and `llama-server` binaries
all come from llama.cpp. The `Q4_K_M` quantisation scheme is llama.cpp's.

## 3. Benchmark datasets (internal accuracy proxy only)

These four tasks form the lm-eval mix in REPORT.md section 4.5. They rank candidates
against each other. **None of them is agronomy**, and none is the competition's accuracy
score, which is produced by judges in conversation.

| Task | Dataset | Citation | Licence |
|---|---|---|---|
| `arc_easy`, `arc_challenge` | AI2 Reasoning Challenge | Clark et al., *Think you have Solved Question Answering? Try ARC, the AI2 Reasoning Challenge*, 2018 (arXiv:1803.05457) | CC BY-SA 4.0 (**unverified**) |
| `mmlu_high_school_biology`, `mmlu_nutrition` | MMLU | Hendrycks et al., *Measuring Massive Multitask Language Understanding*, ICLR 2021 (arXiv:2009.03300) | MIT (**unverified**) |

Both are used through lm-eval's own task definitions and dataset fetching, at build time on
a developer machine. Neither dataset ships in this repository or on any device.

## 4. Candidate models

All six were resolved and downloaded as Q4_K_M GGUF; sha256 of the exact bytes each
measurement ran against is in `competition/candidate_hashes.txt`. Licence and licence
source are **retrieved** from the model cards on the dates recorded in
`competition/candidates.yaml`, which is the authoritative copy of this table.

| Model | GGUF repo | Base model licence | Retrieved |
|---|---|---|---|
| Llama 3.2 1B Instruct | `bartowski/Llama-3.2-1B-Instruct-GGUF` | Llama 3.2 Community License | 12 Aug 2026 |
| Qwen3.5 0.8B | `unsloth/Qwen3.5-0.8B-GGUF` | Apache-2.0 | 12 Aug 2026 |
| Qwen3.5 2B | `unsloth/Qwen3.5-2B-GGUF` | Apache-2.0 | 12 Aug 2026 |
| Qwen3.5 4B | `unsloth/Qwen3.5-4B-GGUF` | Apache-2.0 | 12 Aug 2026 |
| Gemma 4 E2B it | `unsloth/gemma-4-E2B-it-GGUF` | Apache-2.0 | 12 Aug 2026 |
| Phi-4-mini Instruct | `unsloth/Phi-4-mini-instruct-GGUF` | MIT | 12 Aug 2026 |
| SmolLM2 135M Instruct (smoke test only, never a candidate) | `bartowski/SmolLM2-135M-Instruct-GGUF` | Apache-2.0 | 11 Aug 2026 |

The GGUF repositories above are third-party requantisations of the base models. A
repacker's declared licence does not override the base model's terms if the two ever
disagree, and `competition/candidates.yaml` records both.

### What we ship, and why no redistribution obligation attaches

`download_model.sh` fetches the **stock upstream GGUF at a pinned revision**, verifies size
and sha256, and applies our chat template locally before profiling. **We re-host nothing.**
The bytes the judges download are upstream's.

This is a licensing choice as much as an engineering one. Re-hosting a modified GGUF would
attach derivative-redistribution obligations, heaviest for Llama 3.2, whose Community
License requires a derivative model's name to *begin with* "Llama", plus a "Built with
Llama" notice and a bundled copy of the agreement. Baking at download avoids all of it.
Every obligation per candidate is recorded verbatim in `competition/candidates.yaml` under
`redistribution.obligations`, and a test asserts each candidate records them.

## 5. Product-side dependencies

Declared in `requirements.txt`, labelled runtime or build time there.

| Package | Role | Licence |
|---|---|---|
| `numpy` | runtime, vector maths and the brute-force retrieval fallback | BSD-3-Clause (**unverified**) |
| `PyYAML` | runtime, config and locale loading | MIT (**unverified**) |
| `sqlite-vec` | runtime, the single-file vector index | Apache-2.0 / MIT (**unverified**) |
| `sentence-transformers` | build time, embedding at index build | Apache-2.0 (**unverified**) |
| `pypdf`, `python-docx` | build time, ingestion adapters | BSD-3-Clause, MIT (**unverified**) |
| `typer`, `rich` | dev CLI only, never shipped in the APK | MIT (**unverified**) |
| `pytest` | tests | MIT (**unverified**) |

**Embedding model:** `all-MiniLM-L6-v2` (`config.yaml: embedder.path`), Apache-2.0
(**unverified**). Sentence-BERT is Reimers and Gurevych, *Sentence-BERT: Sentence
Embeddings using Siamese BERT-Networks*, EMNLP 2019 (arXiv:1908.10084).

## 6. Agronomic content

**None. There is nothing to attribute, and that is the point.**

Everything in `data/corpus/` is a structural placeholder flagged `placeholder: true`. It
states no date, rate, threshold, or product name, and is excluded from any answer served
outside a development profile. We did not author agronomic content and we did not
incorporate anyone else's.

Content we know we need, and the organisation that would hold each item, is registered as
gaps G-01 to G-14 in `data/SOURCES.md`: AGRITEX, the Plant Protection Research Institute,
the Chemistry and Soil Research Institute, DR&SS, Seed Co, Pannar, the Zimbabwe Seed
Association, CIMMYT Zimbabwe, ICRISAT, FAO Zimbabwe, and CABI Plantwise, among others.
**Naming them here is a statement of where validated content must come from, not a claim
that any of it has been obtained, licensed, or used.** No content from any of these
organisations is present in this repository.

When a gap is filled, the source, publisher and refresh date become required fields on
every chunk derived from it, a named human reviewer signs it off in
`data/review_ledger.jsonl`, and the attribution is added here.
