---
name: chunk-and-embed
description: Chunk cleaned Mhizha corpus documents with full metadata preserved, then embed them with the local quantized sentence embedder. Use when tuning chunk size or overlap, changing the embedder, or re-embedding after a corpus change. Build time only, local models only, no cloud embedding API ever.
---

# chunk-and-embed

Splits cleaned documents into retrievable units and turns each into a vector, without ever
losing the metadata that makes an answer citable.

## When to use

- After `ingest-corpus` adds or replaces documents
- When tuning `corpus.chunk.size` or `corpus.chunk.overlap`
- When swapping the embedder (which forces a full re-embed and re-index)

## Command

```bash
make embed
python -m mhizha embed --force        # re-embed everything
python -m mhizha embed --inspect 5    # print 5 chunks with their metadata
```

## Chunking rules

Config: `corpus.chunk` in `config.yaml`. Defaults chosen for a small-context on-device
model, where a bloated context block costs both KV cache memory and latency.

Never split:

- a table row from its header row (a spray rate without its crop column is dangerous)
- a dosage or mixing rate from its units and its crop
- a spray interval from the pest it applies to
- a numbered step from its procedure heading

Prefer semantic boundaries (headings, list items, table blocks) over a fixed character
count. Overlap exists so a boundary never orphans a qualifier such as "only on soils with
pH above", which inverts an instruction when it is lost.

Every chunk inherits the full document metadata plus `chunk_id`, `doc_id`, `ordinal`,
`char_span`, and its page or section anchor. A chunk that loses `source` or
`refresh_date` is a bug, not a formatting quirk.

## Embedding rules

- Local model only, from a local path. No cloud embedding API, at build time or runtime.
- Model id, dimension, normalisation, and the `multilingual` flag come from `config.yaml`.
- Embed the chunk text plus a compact metadata prefix (crop, region, season) so a query
  naming a region can find a passage that only mentions it in its heading.
- L2-normalise vectors so cosine similarity is a dot product, which keeps the on-device
  fallback path cheap.
- Record the embedder id and dimension alongside the vectors. A mismatch at index-open
  time must be a loud error, never silent garbage retrieval.
- For Shona and Ndebele support, an English-only embedder cannot serve cross-language
  retrieval. Set `multilingual: true` and pick accordingly rather than hoping.

## Rules

- Deterministic: same corpus and same config gives the same vectors.
- Never embed a chunk that failed schema validation.
- Placeholder chunks are embedded but stay flagged, so retrieval can exclude them by
  profile.

## Done

Report chunk count, mean and max chunk length, embedder id and dimension, and time taken.
Then run `pytest tests/test_corpus.py tests/test_retrieval.py`.
