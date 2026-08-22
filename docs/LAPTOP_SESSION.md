# Laptop session: the prompt, and the boundaries

Paste the block below into Claude Code after a **fresh clone**. Not a pull of an old copy:
a stale clone is how the physical-telemetry work gets merged against a tree that no longer
matches the report it is filling (SUBMISSION.md, push topology).

---

```
Read HANDOFF.md first, then SUBMISSION.md. COMPETITION.md is the source of truth and
competition/superseded.yaml lists every conclusion this project has reversed; prefer both
over any recollection.

Before anything else, in this order:
  git status              confirm you are level with origin/master with nothing local
  make setup              installs deps AND fetches the embedder weights. Needs network
  make test               must be green (328 tests) before you change anything
  make doctor             check embedder_id reads all-MiniLM-L6-v2, not hash-fallback

That embedder check matters, though it is now guarded rather than silent: the fallback
defaults off, ask refuses without weights, and open_index raises EmbedderMismatchError if
the index was built by a different embedder than the configured one. Run make build again
if doctor reports a stale index.

Your own earlier work is already merged (bd1c005): the video prerequisites point at the
shipped embedder, and beat 4's dependence on real retrieval is documented. You do not need
to redo it.

State: Gate 1 closes 24 Aug 2026 23:45 PDT. The model is selected (qwen3.5-2b, template
baked, runner-up qwen3.5-4b in config.yaml). metadata.json and download_model.sh are
complete and verified end to end. Submitted telemetry is currently a section 9g FALLBACK
measured on a shared VPS: 3.27 tok/s with 15.0% spread, peak RSS 1433.78 MB. The report
carries no latency figure at all.

You may change exactly two things.

1. PHYSICAL TELEMETRY, only if this machine is near the Standard Laptop spec (4 cores,
   8 GB, no GPU). First say plainly whether it qualifies; if it does not, stop and do not
   run it, because a figure from a machine unlike the audit box is worth less than the
   labelled fallback we already have. If it qualifies:
     - official profiler image only, no flags of ours (the audit-fidelity oracle in
       competition/fidelity_oracle.json binds any run feeding a submitted number)
     - several repetitions, screened, warm-up discarded, median as the central estimate
     - measure nothing else on this machine at the same time. Two concurrent runs
       contaminated a measurement on the VPS on 22 Aug and both had to be discarded
     - stamp the runs host_class: physical
     - then supersede the FALLBACK figures in REPORT.md 4.1 and the section 0 summary,
       drop the FALLBACK labels, and retire the section 9g fallback clause rather than
       leaving it standing as an alternative
     - a physical run also makes judge latency quotable for the first time. It is optional
       and it is the only latency that may ever enter the report.

2. THE VIDEO. docs/VIDEO.md is finished: seven beats, narration written verbatim, 279
   words, 1:55. Record the terminal live rather than showing the saved SVGs. Do not speak
   any number aloud; the script deliberately contains none. If you re-record the captures,
   check the embedder header on them first.

Everything else is frozen. If you believe something else must change, write the reason
down in HANDOFF.md before changing it.

Rules that bind you, all enforced by the suite:
  - No number enters REPORT.md by hand. It is measured (emitted by
    scripts/report_figures.py from a run under runs/), retrieved, or derived.
  - Absence fails closed. A missing measurement is Absent, never zero.
  - Latency is quotable only from a run stamped host_class: physical.
  - The guard layer is frozen. New guards only on a demonstrated failure.
  - Run scripts/scrub_runs.py before staging anything under runs/.
  - make test green before any commit. Check the exit code, do not pipe it to tail.

You cannot push. Commit with clear messages and tell Simba; he pushes. One machine open at
a time.
```

---

## What this session must not do

- **Do not re-open the model selection.** It was made by a candidate-blind read whose
  ordering was committed before the seal was opened. Re-deciding it now, with the mapping
  known, would be the anchor arriving late rather than a more careful decision.
- **Do not rescale `docs/BAKEOFF.md`'s throughput table.** It is understated because the
  sweep interleaved six candidates, and it is left as measured on purpose.
- **Do not force-push or rewrite history.** Decision D-09. If a rewrite happens at all it
  is Simba's, from his machine, before the tag.
