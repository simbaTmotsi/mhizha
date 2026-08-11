---
name: build-index
description: Build the single-file sqlite vector index that ships to the device, using sqlite-vec where available and a numpy brute-force fallback where it is not. Use after chunking and embedding, when changing the index schema, or when preparing an index for APK bundling. Build time only.
---

# build-index

Produces `data/index/mhizha.db`: one sqlite file holding chunks, metadata, and vectors,
shippable in APK assets and openable read-only on a phone with no connectivity.

## When to use

- After `chunk-and-embed`
- When the index schema or metadata filters change
- When preparing a release artefact for the Android build

## Command

```bash
make index
python -m mhizha index --rebuild
python -m mhizha index --stats     # counts, size, backend, embedder id
```

## Why one file

The whole retrieval layer has to be copyable into APK assets and openable read-only by an
app with no network permission and no background service. One file means one thing to
ship, one thing to version, one thing to verify by hash. Anything that needs a server, a
daemon, or a directory of shards is out of scope by rule 2.

## Backends

`src/mhizha/rag/store.py` exposes one interface with two implementations:

1. **sqlite-vec** (preferred). Vectors in a `vec0` virtual table, k-NN in SQL.
2. **numpy fallback**. Vectors as BLOBs in the same file, brute-force cosine over a matrix
   loaded once. Correct at our corpus scale, and it keeps the pipeline runnable anywhere
   the extension will not load.

Both write **the same file layout**, so an index built with the fallback is still a valid
sqlite-vec index once the extension is available. Callers cannot tell which is active
except through `store.backend`, which is reported by `--stats` and by `make doctor`.

## Schema

- `chunks`: chunk_id, doc_id, text, and every metadata field including `source`,
  `publisher`, `refresh_date`, `crop`, `region`, `season`, `topic`, `lang`, `validated`,
  `placeholder`
- `vectors`: chunk_id to vector (vec0 table or BLOB column)
- `index_meta`: embedder id, dimension, normalisation, corpus snapshot hash, build
  timestamp, schema version

`index_meta` exists so that opening an index with the wrong embedder raises immediately.
Silent dimension or model mismatch is the failure mode that produces confident nonsense.

## Rules

- Fully rebuildable from `data/corpus/` alone. The index is a derived artefact and is
  gitignored.
- Metadata filters (crop, region, season, lang, `validated_only`, `placeholder`) must be
  queryable without a rebuild.
- Report the file size. It is a shipping constraint, not a statistic.
- No ANN index, no external service, no second process.

## Done

Report chunk count, vector dimension, backend in use, file size, and the corpus snapshot
hash. Then run `pytest tests/test_retrieval.py`.
