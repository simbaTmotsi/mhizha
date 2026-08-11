# Android packaging and on-device deployment

The dev harness in this repo is a faithful rehearsal of the app, not a different product:
the same `answer_question` path, the same `safety.check` choke point, the same response
object. What changes on Android is the generation runtime and how the assets get onto the
device.

## The strongest enforcement of rule 1

**The app requests no network permission at all.**

```xml
<!-- AndroidManifest.xml deliberately does NOT contain: -->
<!-- <uses-permission android:name="android.permission.INTERNET" /> -->
```

Every other offline guarantee in this codebase is a convention a future change could
erode. This one is enforced by the operating system: with no `INTERNET` permission, a
network call fails at the syscall regardless of what any library tries to do. It also
means no analytics SDK, no crash reporter, and no dependency that quietly phones home can
ever be added without someone deliberately adding the permission back, which is a visible
one-line diff in a manifest.

`tests/test_offline.py` is the build-time counterpart: it fails the build if a runtime
module so much as imports a networking library.

## Assets

Two artefacts ship with the app, both built on a developer machine. The device never
builds its own index and never downloads a model.

| Artefact | Built by | Approx size | Where |
|---|---|---|---|
| `mhizha.db` (chunks + vectors + metadata) | `make index` | ~2 MB today | APK assets |
| `<model>.gguf` | downloaded at build time | ~810 MB | see below |
| Embedder weights | downloaded at build time | ~23 MB int8 | APK assets |
| Locale files | in the repo | tens of KB | APK assets |

**The GGUF cannot go in the APK.** Google Play caps an APK at 200 MB (and an AAB's base
module similarly), so an 810 MB model needs one of:

1. **Play Asset Delivery, install-time or fast-follow.** The model arrives with the app
   from the store. The farmer's device does the transfer once, at install, over whatever
   connection they used to get the app. This does not violate rule 1: rule 1 governs
   inference, not installation, and nothing is fetched when a question is asked.
2. **Sideload or SD card provisioning.** Realistic for the actual deployment context. An
   extension officer or an agro-dealer provisions handsets from a local copy, and no
   farmer ever pays for 810 MB of mobile data. This is the path worth designing for.
3. **A distribution partner image.** If handsets are supplied through a programme, the
   model is part of the image.

Whichever path, the app's first run copies or verifies assets into app-private storage
and checks a hash. A corrupt or absent model must produce the `error.no_model` message,
never a crash and never a silent fallback to answering without retrieval.

## Generation runtime

`src/mhizha/llm/base.py::LLMBackend` is the contract. The Python `llamacpp` backend is the
dev harness. On Android, implement the same contract over one of:

**MediaPipe LLM Inference API.** Google's on-device inference path. Simplest Android
integration, uses `.task` bundles rather than GGUF, so the model conversion step is
different and the shortlist sizes in `docs/model-shortlist.md` need re-measuring for that
format. Supported model set is narrower.

**MLC-LLM.** Compiles the model for the target. Broader model support and generally
better throughput on mid-range hardware, at the cost of a heavier build pipeline and a
per-architecture compile step.

**llama.cpp via JNI.** Most control, closest to the dev harness, most work. Worth it if
the GGUF shortlist is the constraint that matters.

Recommendation for the 4 GB target: prototype against MLC-LLM first, because throughput on
a mid-range CPU is the binding constraint on whether the app feels usable, and MLC gives
the most room there. Keep the decision behind the protocol so it stays reversible.

## Retrieval on device

`sqlite-vec` ships as a loadable extension. On Android that means bundling the `.so` for
each ABI (`arm64-v8a` at minimum, `armeabi-v7a` if older handsets are in scope) and
loading it against the app's sqlite connection.

If the extension will not load on a given device, `src/mhizha/rag/store.py` falls back to
a numpy-style brute-force scan over the same vectors, which are always written as BLOBs in
the same file. At a few thousand chunks that is fast enough on a phone CPU. The fallback
is not a degraded product: `tests/test_retrieval.py::test_both_backends_agree_on_ranking`
asserts both backends return identical rankings and scores.

## Memory at runtime

Budget the whole app together, not component by component. `make doctor` prints the
accounting. On the `low_4gb` profile the margin is under 100 MB, so:

- Load the model once and keep it. Repeated load and unload will thrash.
- Memory-map the sqlite index rather than reading it into heap.
- Keep `llm.context_tokens` at 2048. Raising it raises KV cache, which is a line item in
  the budget, and the passages are short.
- Load the embedder lazily and keep it: it is small, and re-loading it per query is worse
  than holding 23 MB.

## What must be tested on real hardware before shipping

None of these can be settled from a laptop, and all of them are gap G-09:

1. Resident memory of the whole app under sustained use, not just model weights.
2. Time to first token and tokens per second on a representative 4 GB handset.
3. Whether the low-memory killer takes the app when the farmer switches to WhatsApp and
   back, which is the single most likely real-world failure.
4. Battery cost of a typical session.
5. Answer quality of the chosen quantization on grounded extraction, measured with
   `make eval --backend <real>`, not judged by feel.
