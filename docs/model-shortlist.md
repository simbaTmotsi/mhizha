# Model shortlist and device budget

Every size figure here is an estimate from published GGUF and model card sizes. **None
has been measured on a Zimbabwean target handset.** That measurement is gap G-09 in
`data/SOURCES.md` and it is the difference between a model that fits and an app that gets
killed in a field with no signal.

The shortlist lives in code at [`src/mhizha/llm/registry.py`](../src/mhizha/llm/registry.py)
as data. Adding a model means adding a row, never editing branching logic.

## The budget

Active profile: `low_4gb`, a 4 GB RAM Android phone.

| Item | MB | Source |
|---|---|---|
| Total device RAM | 4096 | profile |
| App budget before the low-memory killer | 1400 | profile, conservative estimate |
| less KV cache at 2048 context tokens | 220 | profile |
| less runtime overhead (app, framework) | 180 | profile |
| **Available for weights + embedder + index** | **1000** | derived |

Run `make doctor` for the live accounting against the current config and the built index.

## Generation candidates

| Model | Params | Quant | On disk | Resident (approx) | Context | Licence | Fits 4 GB |
|---|---|---|---|---|---|---|---|
| Llama 3.2 1B Instruct | 1.24B | Q4_K_M | ~810 MB | ~900 MB | 8192 | Llama 3.2 Community | yes |
| Qwen2.5 1.5B Instruct | 1.54B | Q4_K_M | ~1000 MB | ~1100 MB | 32768 | Apache-2.0 | no |
| SmolLM2 1.7B Instruct | 1.71B | Q4_K_M | ~1060 MB | ~1160 MB | 8192 | Apache-2.0 | no |
| Gemma 2 2B it | 2.61B | Q4_K_M | ~1710 MB | ~1850 MB | 8192 | Gemma Terms | no (6 GB yes) |
| Llama 3.2 3B Instruct | 3.21B | Q4_K_M | ~2020 MB | ~2200 MB | 8192 | Llama 3.2 Community | no (6 GB yes) |
| Phi-3-mini 4k Instruct | 3.82B | Q4_K_M | ~2320 MB | ~2500 MB | 4096 | MIT | no |

**Only Llama 3.2 1B currently fits the 4 GB profile**, and it does so with under 100 MB of
headroom once the 90 MB embedder and the index are counted. That margin is real and it is
thin. `tests/test_llm.py::test_four_gb_margin_is_thin_and_index_growth_can_break_it`
locks it in: an index above roughly 10 MB pushes the profile over budget, and the answer
then is a smaller index or a smaller model, not a bigger number in `config.yaml`.

Qwen2.5 1.5B is the most attractive candidate on licence (Apache-2.0) and context length
(32k, which matters for stuffing more passages into a grounded prompt). It misses the
4 GB budget by roughly 100 MB. Two ways it could come back into range, both requiring
measurement first: a Q4_0 or Q3_K_M quantization, or a lower `llm.context_tokens` freeing
KV cache. Neither should be assumed to work without testing answer quality after.

## Quantization

Q4_K_M throughout, as the usual quality-per-megabyte sweet spot for models this small.
The tradeoff worth recording: below Q4, small models degrade noticeably at exactly the
task Mhizha needs, which is faithful extraction from a supplied passage rather than
fluent generation. A model that paraphrases a spray table loosely is more dangerous here
than one that is merely less articulate.

## Embedding

| Model | Dim | fp32 | int8 (approx) | Multilingual |
|---|---|---|---|---|
| all-MiniLM-L6-v2 (**current**) | 384 | ~90 MB | ~23 MB | no |
| bge-small-en-v1.5 | 384 | ~130 MB | ~33 MB | no |
| paraphrase-multilingual-MiniLM-L12-v2 | 384 | ~470 MB | ~120 MB | yes |

The current embedder is **English only**. This is a known limitation, not an oversight:
a Shona or Ndebele query cannot match an English passage through an English-only
embedder, and no amount of prompt engineering fixes that. `make doctor` prints this
warning every run.

Two paths, and they are complementary rather than alternatives:

1. **Swap to a multilingual embedder** (gap G-12). Costs roughly 100 MB int8 against a
   1000 MB budget that already only fits one generation model. Swapping it forces a full
   re-embed and index rebuild, which `index_meta` enforces by refusing to open a
   mismatched index.
2. **Query-side term mapping** (gap G-11). A small local Shona and Ndebele to English
   agronomic term list applied before embedding. Cheap, transparent, inspectable, and it
   follows rule 4: that list is corpus content, so it is sourced and human-validated,
   never invented.

## Deployment

The dev harness runs GGUF through `llama-cpp-python`. The Android app targets MediaPipe
LLM Inference or MLC-LLM behind the same `LLMBackend` protocol, so nothing above
`src/mhizha/llm/` changes. See [android-packaging.md](android-packaging.md).
