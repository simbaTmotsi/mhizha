.PHONY: help setup deps embedder ingest embed index build ask eval test doctor models clean \
        profile profile-image profile-smoke candidates chunk \
        bake bake-minimal chat-probe apply-template upstream simd-compare native-image bench \
        native-acc-image spot-check lmeval composite captures

PY ?= python3
MHIZHA = PYTHONPATH=src $(PY) -m mhizha
Q ?= when should I plant maize in Mashonaland
# Named L, not LANG: make inherits LANG from the shell environment, so `LANG ?= en`
# silently resolves to the caller's locale (en_US.UTF-8) instead of the default.
L ?= en

help:
	@echo "Mhizha: offline on-device agronomy co-pilot"
	@echo ""
	@echo "  make setup                 dependencies + embedder weights (needs network, once)"
	@echo "  make embedder              fetch just the embedder weights"
	@echo "  make ingest                ingest data/raw/ into data/corpus/"
	@echo "  make embed                 chunk and embed the corpus"
	@echo "  make index                 build the single-file sqlite index"
	@echo "  make build                 ingest + embed + index"
	@echo "  make ask Q=\"...\" L=en       ask a question (fully offline, L is en|sn|nd)"
	@echo "  make eval                  run grounding, abstention, and red-team evals"
	@echo "  make test                  run the test suite"
	@echo "  make doctor                report device budget, backends, index health"
	@echo "  make models                list candidate models and their fit"
	@echo "  make clean                 remove derived artefacts"
	@echo ""
	@echo "ADTC 2026 competition path (see COMPETITION.md):"
	@echo "  make profile-image         build the official profiler docker image"
	@echo "  make candidates CANDIDATE=all   download bake-off GGUFs (build time)"
	@echo "  make profile CANDIDATE=<id>     full profiler run, archived under runs/"
	@echo "  make profile-smoke CANDIDATE=<id>  fast run, no accuracy stage"
	@echo "  make bake CANDIDATE=<id>        bake the agronomy posture into the chat template"
	@echo "  make apply-template MODEL=<gguf>   show what the model actually receives"
	@echo "  make chat-probe MODEL=<gguf> TAG=x qualitative pass (internal proxy)"
	@echo "  make simd-compare CANDIDATE=<id>   in-image vs native AVX2 (O-06)"
	@echo "  make bench CANDIDATE=all REPS=3     steal-screened medians (RANKING only)"
	@echo "  make spot-check CANDIDATE=<id>      O-09 gate: native vs in-image accuracy"
	@echo "  make lmeval CANDIDATE=all           lm-eval mix (INTERNAL PROXY)"
	@echo "  make composite                      ranking table with uncertainty bands"
	@echo "  make upstream                   diff upstream repos vs pinned commits"

# Dependencies AND the embedder weights. Both, because a setup that stops at pip leaves a
# fresh clone silently on the hash fallback, which changes every retrieval result.
setup: deps embedder

deps:
	$(PY) -m pip install -r requirements.txt

# Build time, needs network. Idempotent: skips when the weights are already there.
embedder:
	$(PY) scripts/fetch_embedder.py

ingest:
	$(MHIZHA) ingest

embed:
	$(MHIZHA) embed

index:
	$(MHIZHA) index

build: ingest embed index

ask:
	$(MHIZHA) ask "$(Q)" --lang $(L)

eval:
	$(MHIZHA) eval

test:
	PYTHONPATH=src $(PY) -m pytest tests/ -q

doctor:
	$(MHIZHA) doctor

models:
	$(MHIZHA) models list

# ---------------------------------------------------------------- ADTC 2026
# Competition path. Separate from the product path above: none of these targets
# change product behaviour, and `make test` must stay green across all of them.
# See COMPETITION.md.

CANDIDATE ?= smollm2-135m-instruct-q4_k_m

profile-image:
	docker build -t adtc-profiler:latest vendor/adtc-profiler

candidates:
	bash scripts/fetch_candidates.sh $(if $(filter all,$(CANDIDATE)),all,$(CANDIDATE))

# Full run including the accuracy stage. This is what a submitted number must come from.
profile:
	$(PY) scripts/adtc_profile.py --candidate $(CANDIDATE) $(PROFILE_ARGS)

# Fast smoke loop. Never the source of a submitted number.
profile-smoke:
	$(PY) scripts/adtc_profile.py --candidate $(CANDIDATE) --skip-accuracy $(PROFILE_ARGS)

# --- judge-chat path (COMPETITION.md section 7) ---
MODEL ?= models/bakeoff/$(CANDIDATE).gguf
BAKED ?= models/submission/mhizha-$(CANDIDATE).gguf

# Bake the agronomy posture into a candidate's chat template.
bake:
	$(PY) bake_template.py --in $(MODEL) --out $(BAKED)

# Arm 2 of the three-arm A/B: thinking guard only, no persona.
bake-minimal:
	$(PY) bake_template.py --in $(MODEL) --out models/submission/minimal-$(CANDIDATE).gguf --no-persona

# Mandatory gate before submitting any baked model: show exactly what the model receives.
apply-template:
	$(PY) scripts/judge_chat.py --model $(MODEL) --apply-template-only

# Qualitative chat pass, in-image, no client system message. INTERNAL PROXY.
chat-probe:
	$(PY) scripts/judge_chat.py --model $(MODEL) --tag $(TAG)

native-image:
	docker build -f competition/Dockerfile.native -t adtc-native:latest competition/

# O-06: quantify the SIMD penalty. Never a source of submitted numbers.
simd-compare:
	bash scripts/simd_compare.sh $(CANDIDATE)

# Steal-screened, interleaved throughput. RANKING ONLY, never submitted telemetry.
REPS ?= 3
MAX_STEAL ?= 1.0
bench:
	$(PY) scripts/bench_screened.py --candidates $(CANDIDATE) --reps $(REPS) --max-steal $(MAX_STEAL) $(BENCH_ARGS)

# lm-eval mix. INTERNAL PROXY only: S_acc is judge-scored.
TASKS ?= arc_easy,arc_challenge,mmlu_high_school_biology,mmlu_nutrition
LIMIT ?= 50
ACC_IMAGE ?= adtc-profiler:latest

native-acc-image:
	docker build -f competition/Dockerfile.native-acc -t adtc-native-acc:latest competition/

# O-09 gate: do the two builds agree on accuracy? Must pass before the native image is
# used for any ranking run.
spot-check:
	$(PY) scripts/lmeval_mix.py --spot-check --candidate $(CANDIDATE) --tasks arc_easy --limit 25

lmeval:
	$(PY) scripts/lmeval_mix.py --candidates $(CANDIDATE) --tasks $(TASKS) --limit $(LIMIT) --image $(ACC_IMAGE)

# Composite ranking with propagated uncertainty. Ties are the finalist set.
composite:
	$(PY) scripts/composite.py --auto

# Regenerate the CLI captures used in the submission. Runs the shipped entry point, so
# the assets cannot drift from what the software actually does.
captures:
	$(PY) scripts/capture_cli.py

# Run before submitting, around 22 Aug.
upstream:
	bash scripts/check_upstream.sh

clean:
	rm -rf data/index/*.db data/corpus/*.chunks.json eval/reports
	find . -name __pycache__ -type d -exec rm -rf {} + 2>/dev/null || true
