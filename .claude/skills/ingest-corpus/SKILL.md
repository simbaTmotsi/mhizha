---
name: ingest-corpus
description: Ingest raw agronomic source documents (markdown, txt, PDF, DOCX) from data/raw/ into the Mhizha corpus with provenance and required metadata. Use when new source material arrives, when re-ingesting a revised source, or when adding a new file-format adapter. Build time only, never runs on device.
---

# ingest-corpus

Turns a file in `data/raw/` into cleaned documents in `data/corpus/` carrying provenance
that will still be defensible a year from now.

## When to use

- New extension material, variety guide, or pest sheet lands in `data/raw/`
- A source is revised and needs re-ingestion
- A new format adapter is needed

## Command

```bash
make ingest                       # everything in data/raw/
python -m mhizha ingest --path data/raw/agritex_maize_2024.pdf
python -m mhizha ingest --dry-run # report what would be ingested, write nothing
```

## Required metadata

Ingestion **fails** without these. This is deliberate. A chunk we cannot attribute is a
chunk we cannot defend to a farmer or an extension officer.

| Field | Why it is required |
|---|---|
| `source` | The document title a farmer or officer can go and check |
| `publisher` | Who stands behind the claim (AGRITEX, Seed Co, FAO, CIMMYT) |
| `refresh_date` | Agronomic advice ages. An undated planting calendar is a liability |
| `lang` | `en`, `sn`, or `nd` |

Captured automatically: `doc_id`, `sha256`, `ingested_at`, `source_path`, page or section
anchors, `placeholder`, `validated: false`.

Front matter on a markdown source supplies the required fields directly. For PDF and DOCX,
supply them via a sidecar `<filename>.meta.yaml` or the `--meta` flag. Never guess them
from the filename.

## Steps

1. Detect format, dispatch to the adapter in `src/mhizha/corpus/ingest.py`.
2. Extract text with anchors. Preserve tables as structured text: fertiliser rates and
   spray schedules are the highest-value and most dangerous-to-mangle content in the corpus.
3. Clean via `corpus/clean.py`: unicode and whitespace normalisation, hyphenation repair
   across line breaks, header, footer, and page-number strip.
4. Validate against `corpus/schema.py`. Missing required field means quarantine with a
   clear reason, not a default value.
5. Write to `data/corpus/`, atomically replacing any previous version of the same source.
6. Register anything the source was expected to cover but did not in `data/SOURCES.md`.

## Rules

- Re-ingesting a changed source **re-opens validation**. Previous human sign-off applied
  to previous text.
- Never infer `refresh_date` from file mtime and never default it to today.
- Never invent content to patch an extraction failure. A garbled table is quarantined and
  reported, not smoothed over.
- Network access is permitted here (build time only) but must be explicit and logged.

## Done

Report ingested count, quarantined count with reasons, per-crop and per-region coverage,
and new gaps registered. Then run `pytest tests/test_corpus.py`.
