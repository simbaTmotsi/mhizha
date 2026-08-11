---
name: retrieval-qa
description: Run and debug the grounded question-answering path for Mhizha: retrieve, score confidence, decide answer or abstain, compose the grounded prompt, generate, and cite. Use when an answer is wrong, unsourced, or missing, when tuning top-k or the abstention threshold, or when checking that abstention still fires correctly. Runtime path, fully offline.
---

# retrieval-qa

The end-to-end answer path, and the tools to work out why it did what it did.

## When to use

- An answer is wrong, ungrounded, missing a citation, or missing entirely
- Abstention fired when it should not have, or did not fire when it should have
- Tuning `retrieval.top_k` or `retrieval.abstain_below`
- Verifying the grounded prompt actually reaches the model as intended

## Command

```bash
make ask Q="when should I plant maize in Mashonaland"
python -m mhizha ask "..." --lang sn
python -m mhizha ask "..." --explain     # passages, scores, prompt, decision trace
python -m mhizha ask "..." --json        # machine-readable response object
```

Reach for `--explain` first. Nearly every bad answer is a retrieval problem wearing a
generation costume, and the trace tells you which one you have in under a minute.

## The path

1. **Normalise.** Detect or accept language, normalise the query.
2. **Retrieve.** Top-k with metadata filters. `validated_only` per profile.
3. **Score confidence.** Composite of top-1 similarity, top-1 to top-k margin, and
   agreement across the retrieved set. Documented in `rag/retrieve.py`.
4. **Decide.** Below `retrieval.abstain_below`, do not call the model at all. Abstain or
   ask exactly one clarifying question. Not calling the model is the point: a model given
   weak context will still produce fluent prose.
5. **Ground.** Compose the prompt from retrieved passages only, each carrying its id.
6. **Generate.** Backend from config. Temperature 0 in tests.
7. **Safety pass.** `app/safety.py`, always, no bypass flag.
8. **Assemble.** Answer, sources (title, publisher, refresh date, chunk id), confidence
   band, and abstention state.

## Non-negotiables

- The model is never called without retrieved context. There is no direct-ask code path.
- An answer without sources is never displayed. If citations are missing, that is an
  abstention, not a formatting problem to patch downstream.
- Sources are shown by default, never behind a flag, never truncated to one.
- Confidence is shown to the user as a plain-language band in their language.
- No network call anywhere in this path.

## Debugging order

1. Is the passage even in the corpus? (`grep` `data/corpus/`. If not, it is a corpus gap,
   hand it to `corpus-curator`.)
2. Was it retrieved? (`--explain`. If not, it is a chunking or embedding problem.)
3. Was it retrieved but ranked low? (Chunk size or metadata prefix problem.)
4. Retrieved and ranked well but the answer ignored it? (Prompt problem.)
5. Answer good but the safety pass stripped it? (Check which rule fired and whether it
   should have.)

## Done

The specific question behaves correctly, a test covering it exists in
`tests/test_retrieval.py` or `tests/test_safety.py`, and `make eval` shows no regression
in abstention or red-team categories.
