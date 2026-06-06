# Changelog

## [Unreleased]

### Phase 3 — Benchmark Results
- Benchmark results, charts, and final agentic log to be added after Phase 2 deployment

---

## [0.2.0] — Phase 2: Deployment (in progress)

### Added
- Real API credentials configured (not committed)
- Verified model IDs on both platforms
- Deployment notes populated in `deploy/simplismart_notes.md` and `deploy/fireworks_notes.md`
- AGENTIC_LOG.md entries from deployment experience

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
- `benchmark/report.py` — markdown table, 3 matplotlib charts, narrative summary
- `tests/test_runner.py` — unit tests with zero real API calls
- `requirements.txt` — Python dependencies
- `Makefile` — targets: setup, dry-run, benchmark-p0, benchmark-all, report, test, clean
- `deploy/simplismart_notes.md` — structured template for deployment observations
- `deploy/fireworks_notes.md` — structured template for deployment observations
- `README.md` — full project documentation with model rationale, setup instructions, cost estimates

### Verified
- `python -m benchmark.runner --dry-run` passes without API keys
- `pytest tests/` passes all tests
