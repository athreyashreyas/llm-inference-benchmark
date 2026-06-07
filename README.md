# LLM Inference Benchmark: Simplismart vs Fireworks AI

A benchmark comparing the inference performance and agentic developer experience of [Simplismart](https://simplismart.ai) and [Fireworks AI](https://fireworks.ai), produced as part of an Associate Product Manager hiring task.

The primary output of this project is not the performance numbers — it is the agentic UX analysis captured in [AGENTIC_LOG.md](AGENTIC_LOG.md): a real-time record of every friction point encountered while attempting to deploy and benchmark both platforms entirely programmatically.

**Want to run this yourself?** Jump straight to the [Reproduction Guide](#reproduction-guide) for step-by-step setup and benchmark-run instructions.

---

## What This Project Is

This project attempts to answer a product question: *How well do these platforms support developers building agentic, autonomous workflows?*

The benchmark is the vehicle. The agentic deployment experience — what could be scripted, what required manual UI steps, what failed without useful error messages — is the finding.

---

## Why Gemma 3 4B

**Primary model**: Gemma 3 4B Instruct (`google/gemma-3-4b-it`)

| Criterion | Rationale |
|-----------|-----------|
| Not covered by Simplismart tutorials | Simplismart has a detailed vLLM deployment guide for Llama 3.1 8B. Using it would follow their tutorial and obscure the deployment discovery experience this task is designed to evaluate. |
| Cheapest non-trivial model on Simplismart | $0.10/1M tokens — most budget-safe for a $5 credit ceiling |
| Available on both platforms as dedicated H100 | Confirmed deployable on Simplismart and Fireworks AI dedicated H100 endpoints |
| Current-generation architecture | Released 2025; compact 4B model well-suited for latency-focused benchmarking |
| Budget-safe GPU fit | 4B params (~8GB VRAM) fits comfortably on H100 80GB with significant headroom |
| Apache 2.0 license | No commercial restrictions |

**Llama 3.1 8B was explicitly excluded** because Simplismart's own blog covers its deployment step-by-step, which would make this submission look like a tutorial playthrough rather than independent product evaluation.

---

## Why Fireworks AI

- **OpenAI-compatible API**: same benchmark code works for both platforms with only base URL + key swapped
- **Serverless-first architecture**: no GPU provisioning required; scale-to-zero built in; similar to Simplismart's marketplace vs dedicated endpoint option
- **Developer-focused positioning**: directly comparable target market to Simplismart
- **$5 free credits**: sufficient for this benchmark at ~$0.20/1M tokens (4B–16B models)
- **Strong inference throughput reputation**: credible competitive reference point

---

## Repository Structure

```
llm-inference-benchmark/
├── README.md               ← You are here — see "Reproduction Guide" below to run this yourself
├── USAGE_OF_AI.md          ← How Claude Code was used throughout
├── ASSUMPTIONS.md          ← All assumptions documented before coding
├── AGENTIC_LOG.md          ← The primary PM output: real-time friction log
├── CHANGELOG.md
├── .env.example            ← Template — never commit a real .env
├── .gitignore
├── requirements.txt
├── Makefile
├── config/
│   ├── platforms.yaml      ← API config (env var references only)
│   └── benchmark.yaml      ← Scenario parameters
├── benchmark/
│   ├── runner.py           ← Async benchmark runner
│   ├── metrics.py          ← Aggregation and CSV output
│   ├── prompts.py          ← Prompt loading utilities
│   └── report.py           ← Chart and table generation
├── data/
│   ├── prompts.json        ← 30 benchmark prompts
│   └── results/            ← Raw and summary CSVs (gitignored raw)
├── report/
│   ├── REPORT.md           ← Full benchmark report: results, analysis, validation
│   ├── charts/             ← Generated PNG charts
│   └── screenshots/        ← Manual screenshots from platform UIs
├── tests/
│   └── test_runner.py      ← Unit tests (zero real API calls)
└── deploy/
    ├── deploy_simplismart.py    ← Compile + deploy via Simplismart SDK
    ├── deploy_fireworks.py      ← Deploy via Fireworks REST API
    ├── teardown_simplismart.py  ← Tear down Simplismart deployment
    ├── teardown_fireworks.py    ← Tear down Fireworks deployment
    ├── simplismart_notes.md
    └── fireworks_notes.md
```

---

## Reproduction Guide

Step-by-step instructions to set up the project and reproduce the benchmark runs and reports from scratch.

### Setup

**Prerequisites**: Python 3.11+

```bash
# 1. Clone the repo
git clone <repo-url>
cd llm-inference-benchmark

# 2. Create virtual environment and install dependencies
make setup

# 3. Copy env template and fill in your API keys
cp .env.example .env
# Edit .env: add your Simplismart and Fireworks API keys
# IMPORTANT: Verify exact model ID strings in each platform's UI before running

# 4. Activate the venv
source .venv/bin/activate

# 5. Validate config without making any API calls
make dry-run
```

### Running the Benchmark

```bash
# P0 scenarios only (~180 requests, ~$0.05 estimated)
make benchmark-p0

# All scenarios (~280 requests, ~$0.10 estimated)
make benchmark-all

# Generate comparison table and charts after benchmarking
make report

# Run tests
make test
```

### CLI flags for granular control

```bash
python -m benchmark.runner --dry-run
python -m benchmark.runner --platform simplismart --priority p0
python -m benchmark.runner --platform fireworks --priority all
python -m benchmark.runner --scenarios E01,E02,E06,E07
```

---

## Experiment Matrix

| ID | Platform | Prompt Type | Max Output | Concurrency | Reps | Priority |
|----|----------|-------------|-----------|-------------|------|---------|
| E01 | Simplismart | Short Q&A | 50 tokens | 1 | 15 | P0 |
| E02 | Simplismart | Medium gen | 150 tokens | 1 | 15 | P0 |
| E03 | Simplismart | Short Q&A | 50 tokens | 5 | 15 | P0 |
| E04 | Simplismart | Medium gen | 150 tokens | 5 | 10 | P1 |
| E05 | Simplismart | Long instr | 200 tokens | 10 | 10 | P1 |
| E06 | Fireworks AI | Short Q&A | 50 tokens | 1 | 15 | P0 |
| E07 | Fireworks AI | Medium gen | 150 tokens | 1 | 15 | P0 |
| E08 | Fireworks AI | Short Q&A | 50 tokens | 5 | 15 | P0 |
| E09 | Fireworks AI | Medium gen | 150 tokens | 5 | 10 | P1 |
| E10 | Fireworks AI | Long instr | 200 tokens | 10 | 10 | P1 |

---

## Estimated Costs

| Run | Requests | Estimated cost |
|-----|----------|---------------|
| P0 only | ~180 | < $0.05 |
| Full benchmark | ~280 | < $0.10 |
| Dedicated GPU (H100) | — | < $1.00 at $2.00/hr H100 |

**Hard limit**: $4.50/platform abort threshold is coded into the runner. Neither platform's $5 credit will be exceeded.

---

## Pre-committed vs Reproducible Results

| Artifact | Pre-committed? | Requires live deployment? |
|----------|---------------|--------------------------|
| `data/prompts.json` | Yes | No |
| `data/results/summary_*.csv` | Yes (after Phase 3) | No — read pre-committed |
| `data/results/*_raw.csv` | No (gitignored) | Yes |
| `report/charts/*.png` | Yes (after Phase 3) | No — read pre-committed CSVs |
| `deploy/` notes | Yes | No — observational |

To reproduce raw results, you need API keys for both platforms and should expect minor variation due to shared infrastructure and network conditions — see the [Reproduction Guide](#reproduction-guide) above for the exact steps.

---

## Limitations

- Results are from a single session on dedicated H100 infrastructure. They are indicative, not statistically definitive.
- Network latency differences between platforms are not controlled for.
- Token counts fall back to approximate counting when the API `usage` field is absent in streaming responses.

Full assumption set: [ASSUMPTIONS.md](ASSUMPTIONS.md)

---

## How AI Was Used

Claude Code (the Anthropic CLI agent) was used for the entire project — repo scaffolding, module implementation, test writing, report generation, and documentation. See [USAGE_OF_AI.md](USAGE_OF_AI.md) for the full task-by-task log.

The agentic-first approach is itself a product observation: using an AI coding agent to attempt full programmatic deployment surfaces exactly the friction points that matter for developer experience on these platforms.

---

## Contact

Produced by Shreyas Athreya as part of the Simplismart APM hiring task.
