---
name: localize
description: Add or update Mhizha user-facing strings and locale handling for English, Shona (sn), and Ndebele (nd), including cross-language retrieval concerns. Use when adding any user-facing string, adding a locale, or when a query in one language fails to retrieve corpus content in another. No user-facing string is ever hardcoded in code.
---

# localize

Keeps every user-facing string out of the code and in a locale file, and keeps the
cross-language retrieval seam honest.

## When to use

- Any time you add a user-facing string. Any time.
- Adding or updating `sn` or `nd` copy
- A Shona or Ndebele query fails to retrieve English corpus content

## Command

```bash
python -m mhizha i18n check       # missing keys, untranslated keys, orphaned keys
python -m mhizha i18n add <key>   # adds to all locales, marks TODO_TRANSLATE
python -m mhizha ask "..." --lang sn
```

## Structure

`src/mhizha/i18n/locales/{en,sn,nd}.yaml`. `en` is the reference: a key that exists in `sn`
but not `en` is an error, not a feature.

Untranslated values are the literal marker `TODO_TRANSLATE`. At runtime the English value
is served and the fallback is **recorded on the response object** as `fallback_from`, and
shown in `--explain`. Silent fallback hides how much of the product a Shona-speaking
farmer is actually getting in English, which is exactly the number we need to see.

## Rules

- No user-facing string literal in code. Ever. `i18n.t(key, lang)` or it does not ship.
- Safety copy (the agrochemical notice, the abstention wording, the AGRITEX referral) is
  **priority for human translation** and must be marked as such. A safety warning served in
  a language the reader does not speak is not a safety warning. Machine translation is not
  acceptable for these keys.
- Translations come from fluent speakers, ideally with agricultural extension familiarity.
  Agronomic vocabulary in Shona and Ndebele is specialised: pest names, crop stages, and
  soil terms have established local usage that a general translator will miss.
- Never machine-translate agronomic content or safety copy into the corpus or the locales.
  Register the need in `data/SOURCES.md` instead.

## Cross-language retrieval

The corpus will be mostly English long before the interface is. Two seams:

1. **Multilingual embedder.** Set `embedder.multilingual: true` in config and choose a
   model that supports it. An English-only embedder cannot match a Shona query to an
   English passage, and no amount of prompt work fixes that.
2. **Query-side term mapping.** A small local Shona and Ndebele to English agronomic term
   list applied before embedding. Cheap, transparent, and inspectable, which matters more
   than elegance here. That list is corpus content and follows rule 4: it is sourced and
   human-validated, never invented.

Answer language is the farmer's language even when passages are English. Cited source
titles stay in their original language, because that is what the farmer would be looking
for if they went to find the document.

## Done

`python -m mhizha i18n check` clean, no hardcoded strings introduced, any new safety copy
flagged for human translation, and translation gaps registered.
