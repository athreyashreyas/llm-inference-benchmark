# Changelog

## [0.4.0] — 2026-08-03 — Reframe as a standalone benchmark project

### Changed
- `README.md` — added a **Headline Results** section up front (comparison table plus the three conclusions worth carrying away), so the payoff is readable without opening the report. Rewrote the intro and "What This Project Is" to state the two-part question the project answers.
- `claude_code_instructions.md` → **`PROJECT_BRIEF.md`** — same brief, reframed as the project's own baseline specification. Removed the framing that only made sense in its original context.
- `AGENTIC_LOG.md` — retitled "Developer Experience Log"; header now states the entry count and the analytical frame. All 13 findings unchanged.
- `USAGE_OF_AI.md`, `ASSUMPTIONS.md`, `report/REPORT.md` — reworded the handful of passages that referenced an external specification or reader. No numbers, methodology, or findings touched.

### Note
No benchmark data, chart, or metric changed in this release — it is a documentation and framing pass only.

---

## [0.3.1] — 2026-06-08 — Consistency pass: align cost and request-count figures across the repo

### Changed
- `README.md` — rewrote "Estimated Costs": removed the est.→actual token-spend tables and sub-cent figures (`~$0.0007`, `~$0.0017`); replaced with authoritative per-token pricing ($0.10/M Simplismart vs $0.20/M Fireworks) and total task spend (≈$1.73 vs ≈$1.70); kept GPU-hour cost table and the $4.50/platform abort guard
- `report/REPORT.md` — Cost section rewritten to state per-token pricing and total spend explicitly, and to explain why a 2× per-token gap coexists with near-equal totals (GPU-hours dominate, token spend negligible); removed the unsupported "~13,000 tokens / ~$0.0026" claim
- `report/REPORT.md` — Summary table: "Cost per token — Tie — $0.10/M on both" → "Cost per M tokens — Simplismart — $0.10 vs $0.20 — 2× cheaper"
- `report/REPORT.md` — corrected stale request-count references ("280 total requests, 130 per platform" → "130 total, 65 per platform"; "130 requests/platform" → "65 requests/platform") to match the experiment matrix and `data/results/summary_ba442d8d.csv`
- Standardized the cold-start multiple to "~9×" (was "~6–9×") in the Summary table

---

## [0.3.0] — 2026-06-07 — Phase 3: Benchmark Results

### Added
- `report/REPORT.md` — full benchmark results with analysis and summary table
- `report/charts/` — 6 PNG charts: TTFT, TPOT, ITL, throughput, latency vs concurrency, p99 tail
- `data/results/summary_72b46d09.csv` — committed summary CSV for P0 scenarios (6 scenarios, 90 requests per platform)
- `benchmark/report.py` — chart and narrative generation from summary CSV

### Results summary
- Simplismart mean TTFT (warm, concurrency=1): 152 ms vs Fireworks 1,343 ms (8.3× faster)
- TPOT equal on both platforms: ~4 ms (same GPU class, same model)
- Simplismart output throughput at concurrency=1: 4–5× higher than Fireworks
- Both platforms: 100% request success rate, 45 requests each (P0 scenarios)

---

## [0.2.0] — 2026-06-06/07 — Phase 2: Deployment and Benchmarking

### Added
- `deploy/deploy_simplismart.py` — full compile-then-deploy script with idempotency, `--deploy-only` flag, COST CHECKPOINT, verbose error logging
- `deploy/deploy_fireworks.py` — REST-based deployment script with H100 targeting, shape discovery fallback, COST CHECKPOINT
- `deploy/teardown_simplismart.py` — deployment deletion via SDK, clears `.env` vars
- `deploy/teardown_fireworks.py` — REST DELETE with `?ignoreChecks=true` to bypass recent-inference guard
- `config/platforms.yaml` — added `extra_headers.id` for Simplismart dedicated deployment routing
- `benchmark/runner.py` — updated `load_platform_config()` to handle nested dicts; `run_platform()` passes extra headers to AsyncOpenAI
- `benchmark/metrics.py` — pricing updated for Gemma 3 4B Instruct on dedicated H100
- Makefile targets: `deploy-simplismart-only`, `teardown-all`
- `.env.example` — completed with all fields including `SIMPLISMART_MODEL_REPO_UUID`, `FIREWORKS_MODEL_ID`
- AGENTIC_LOG.md — 5 Phase 2 entries documenting real deployment friction

### Changed
- Model: Qwen3 4B → Qwen3 14B → Gemma 3 4B Instruct (`google/gemma-3-4b-it`) — Qwen3 4B was on Simplismart's pricing page but absent from its marketplace; the Qwen3 14B fallback then hit a 404 on Fireworks H100 (only H200 offered for that model); gemma-3-4b-it was the first model confirmed deployable with H100 on both platforms (full chain in AGENTIC_LOG.md)
- GPU: A100 → H100 80GB — A100 has zero quota on Simplismart despite being listed as valid

### Discovered friction points
1. Simplismart `create_deployment()` returns 500 but silently creates the deployment — no ID in error response
2. Simplismart inference requires non-standard `id: <deployment_uuid>` header — undocumented in quickstart
3. Simplismart A100 has zero quota despite appearing in SDK enum
4. Fireworks `deploymentShapeVersions` returns 404 for all accounts — shape discovery path unusable
5. Fireworks H100 availability is model-dependent with no programmatic pre-check

---

## [0.1.0] — 2026-06-06 — Phase 1: Repository Build

### Added
- Full repository structure created from specification
- `ASSUMPTIONS.md` — 12 documented assumptions covering model choice, deployment type, budget, and methodology
- `AGENTIC_LOG.md` — initialised with format reference and session bootstrap entry
- `USAGE_OF_AI.md` — initialised with Phase 1 entries
- `config/platforms.yaml` — platform API config with env var references
- `config/benchmark.yaml` — generation parameters, warmup, timeouts, retry, cost guard
- `.env.example` — env template with inline guidance on where to find each value
- `.gitignore` — secrets and runtime artifacts excluded
- `data/prompts.json` — 30 benchmark prompts (15 short, 10 medium, 5 long) spanning geography, science, history, coding, math, writing
- `benchmark/runner.py` — async runner with streaming TTFT, concurrency control, cost guard, retry logic, dry-run flag
- `benchmark/metrics.py` — aggregation (mean, p50, p95, p99), CSV persistence
- `benchmark/prompts.py` — prompt loading and sampling utilities
- `benchmark/report.py` — markdown table, matplotlib charts, narrative summary
- `tests/test_runner.py` — unit tests with zero real API calls
- `requirements.txt` — Python dependencies
- `Makefile` — targets: setup, dry-run, benchmark-p0, benchmark-all, report, test, clean
- `deploy/simplismart_notes.md` — structured template for deployment observations
- `deploy/fireworks_notes.md` — structured template for deployment observations
- `README.md` — full project documentation with model rationale, setup instructions, cost estimates

### Verified
- `python -m benchmark.runner --dry-run` passes without API keys
- `pytest tests/` passes all tests
