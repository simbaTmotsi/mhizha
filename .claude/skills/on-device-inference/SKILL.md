---
name: on-device-inference
description: Select, load, and run a quantized local LLM for Mhizha inside the device RAM budget, across stub, llama.cpp, and Android runtimes. Use when adding or swapping a generation backend, evaluating a candidate GGUF against the budget, or diagnosing slow, oversized, or crashing inference. Never hardcode a model name.
---

# on-device-inference

Getting tokens out of a small model on a small phone, without exceeding the budget that
keeps the app alive.

## When to use

- Adding or swapping a backend (stub, llama.cpp, MediaPipe LLM Inference, MLC-LLM)
- Evaluating a candidate model against the device profile
- Inference is slow, memory-hungry, or the app is being killed

## Command

```bash
make doctor                                  # budget report against active profile
python -m mhizha models list                 # shortlist with sizes and fit verdict
python -m mhizha models fit --profile low_4gb
```

## The budget

From `config.yaml: device`. Primary profile is a 4 GB Android phone, which gives an app
roughly 1.2 to 1.8 GB before the low-memory killer takes it. Everything shares that:

| Component | Notes |
|---|---|
| LLM weights | Largest item. Q4_K_M is the usual sweet spot |
| KV cache | Scales with context length. A large context block is a memory cost, not free |
| Embedder | Int8 quantized, tens of MB |
| Index | One sqlite file, mapped not loaded where possible |
| App and runtime | Headroom, not an afterthought |

A model that does not fit is out, whatever its benchmark scores. On a 4 GB device this
means the 1B to 2B class at Q4, not 3B and not Phi-3-mini. See `docs/model-shortlist.md`
for candidates with their sizes and licences.

## Backends

All implement `src/mhizha/llm/base.py::LLMBackend`. Swapping runtime must never touch app
logic.

- **stub**: deterministic extractive. Default in a fresh checkout. Used by the test suite
  so tests never depend on model weights, and used to prove that a safety property holds
  independent of the generator.
- **llamacpp**: `llama-cpp-python`, GGUF from `models/`. The dev harness.
- **Android**: MediaPipe LLM Inference or MLC-LLM. See `docs/android-packaging.md`.

## Prompt discipline

`src/mhizha/llm/prompts.py`, per locale. The context block contains retrieved passages and
nothing else, each with its id. The instruction block forbids using anything outside the
passages and requires the model to say it does not know when they do not cover the
question. Citations come back as passage ids so grounding can be verified mechanically
rather than trusted.

Keep the prompt short. On a 1B model, every token of preamble competes with the passages
themselves for both attention and KV cache.

## Rules

- No model name outside `config.yaml` and `llm/registry.py`.
- Size figures are measured or marked `(approx, unverified)`.
- Temperature 0 and a fixed seed in tests and evals.
- Never call the model without retrieved context, not even behind a debug flag.
- Record the quantization tradeoff, not just the filename.

## Done

`make doctor` fits the budget, `pytest tests/test_llm.py` green with the stub, and any new
candidate documented with its measured size and licence.
