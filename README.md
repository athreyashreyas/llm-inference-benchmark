# LLM Inference Benchmark: Simplismart vs Fireworks AI

A head-to-head benchmark of the inference performance and developer experience of [Simplismart](https://simplismart.ai) and [Fireworks AI](https://fireworks.ai) — same model, same GPU class, same client code, one session.

Two things came out of it. The obvious one is the latency and throughput numbers. The less obvious one — and the reason the project was worth doing — is [AGENTIC_LOG.md](AGENTIC_LOG.md): a real-time record of every friction point hit while trying to deploy and benchmark both platforms *entirely programmatically*, with no manual UI steps.

**Results:** the full write-up — tables, charts, analysis, and a run-to-run validation against an independent redeployment — is in [report/REPORT.md](report/REPORT.md) (run ID `ba442d8d`, all 10 scenarios E01–E10, validated against baseline run `72b46d09`).

**Want to run this yourself?** Jump straight to the [Reproduction Guide](#reproduction-guide) for step-by-step setup and benchmark-run instructions.

---

## What This Project Is

I wanted to understand what actually differs between two inference platforms once you get past the marketing page — and, separately, how far you can get on either one without ever opening a browser.

So the question this repo tries to answer is two-part: *how do these platforms compare on the metrics that matter for an interactive LLM application (TTFT, TPOT, throughput, cold start, cost), and how well do they support a developer — or an agent — driving them end-to-end from code?*

The benchmark is the vehicle. The deployment experience — what could be scripted, what required manual UI steps, what failed without a useful error message — turned out to be the more interesting half.

---

## Headline Results

Gemma 3 4B Instruct on a dedicated 1× H100 on each platform, 130 requests across 10 scenarios, 100% success rate on both. Full numbers in [report/REPORT.md](report/REPORT.md).

| | Simplismart | Fireworks AI | Verdict |
|---|---|---|---|
| Mean TTFT (warm, concurrency=1) | **145 ms** | 1,024 ms | Simplismart ~7× faster |
| Mean TPOT | 4.2–5.0 ms | 4.6–6.2 ms | Effectively a tie |
| Output throughput (concurrency=1) | **132–189 tok/s** | 32–94 tok/s | Simplismart 3–4× higher |
| Output throughput (concurrency=10, 200-tok gen) | 488 tok/s | **740 tok/s** | Fireworks wins under load |
| Cold start | **503 ms** | 4,349 ms | Simplismart faster and far more consistent |
| Time to first deployment | ~15 min (compile step) | **130 s** | Fireworks much quicker to iterate |
| Price per 1M output tokens | **$0.10** | $0.20 | Simplismart 2× cheaper |

Three things I took away from this:

1. **TPOT is a property of the GPU; TTFT is a property of the platform.** Same model, same H100, and steady-state token generation lands within a millisecond of each other. The 7× gap sits entirely in the time before the first token — routing, queueing, and scheduling in each platform's serving layer. If you're building anything interactive, that's the number to shop on, and it's the one least likely to appear on a pricing page.
2. **The throughput ranking flips with concurrency.** Simplismart wins at concurrency 1–5; Fireworks overtakes it at concurrency=10 with long generations (740 vs 488 tok/s). A single-number "tokens/sec" comparison would have picked a winner and been wrong for half the workloads.
3. **On dedicated endpoints, per-token pricing is nearly irrelevant.** Fireworks costs 2× per token, but total spend came out within 2% of Simplismart's, because GPU-hours dominate the bill. The cost lever is teardown discipline, not the rate card.

---

## Why Gemma 3 4B

**Primary model**: Gemma 3 4B Instruct (`google/gemma-3-4b-it`)

| Criterion | Rationale |
|-----------|-----------|
| Not covered by Simplismart tutorials | Simplismart has a detailed vLLM deployment guide for Llama 3.1 8B. Following it would have handed me a pre-solved deployment path and hidden exactly the discovery experience I was trying to observe. |
| Cheapest non-trivial model on Simplismart | $0.10/1M tokens — most budget-safe for a $5 credit ceiling |
| Available on both platforms as dedicated H100 | Confirmed deployable on Simplismart and Fireworks AI dedicated H100 endpoints |
| Current-generation architecture | Released 2025; compact 4B model well-suited for latency-focused benchmarking |
| Budget-safe GPU fit | 4B params (~8GB VRAM) fits comfortably on H100 80GB with significant headroom |
| Apache 2.0 license | No commercial restrictions |

**Llama 3.1 8B was explicitly excluded** because Simplismart's own blog covers its deployment step-by-step. Benchmarking it would have been a tutorial playthrough rather than an independent evaluation.

---

## Why H100 (and not A100, L40S, or something cheaper)

**GPU**: NVIDIA H100 80GB — dedicated, 1× per platform.

H100 wasn't picked first on cost grounds — it's what survived two rounds of availability discovery that the model choice itself was entangled with (full story in [AGENTIC_LOG.md](AGENTIC_LOG.md)):

| GPU | Why it's not what we ran on |
|---|---|
| **A100 80GB** | Listed as a valid `accelerator_type` in Simplismart's SDK enum and deployment UI — but compilation failed with `HTTP 400: "gpu a100: need 1 but only 0.0 available"`. The account had zero A100 quota despite the platform advertising it as selectable, with no way to discover that short of attempting the deploy. |
| **L40S / L4 / T4 / other lower-tier cards** | Never reached evaluation. The *model* search itself had already turned into a two-platform compatibility hunt — Qwen3 4B was on Simplismart's pricing page but absent from its marketplace; the fallback Qwen3 14B was available on Simplismart but Fireworks only offers `NVIDIA_H200_141GB` for that model, not H100; Gemma 3 4B Instruct was the first model confirmed deployable on H100 on **both** platforms. Adding "and which of these also runs on a cheaper GPU on both platforms" would have meant repeating that same opaque discovery loop a third time, for a benchmark whose total inference-token spend came in under $0.01 either way. |
| **H100 80GB** ✅ | The first accelerator that was *actually provisionable* (not just listed) for a model that was *actually deployable* on both Simplismart and Fireworks AI — the hard constraint for a same-model, same-GPU-class, head-to-head comparison. A 4B-parameter model needs roughly 8GB of the 80GB on offer, so GPU choice has effectively zero bearing on the latency/throughput numbers in this report — a cheaper card would move the cost line, not the comparison. At ~$2/hr with a sub-hour session on each platform, H100 was already comfortably inside the budget I'd set myself. |

**The finding that matters more than the GPU pick itself**: on both platforms, the *advertised* set of valid GPUs (SDK enums, pricing pages, UI dropdowns) didn't match the *actually provisionable* set for this account and this model. Surfacing that mismatch — not optimizing for the cheapest card — is what actually determined the final H100-on-Gemma-3-4B configuration, and it's logged as a first-class friction point in [AGENTIC_LOG.md](AGENTIC_LOG.md).

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
├── PROJECT_BRIEF.md        ← The brief I wrote for the coding agent before any file existed
├── USAGE_OF_AI.md          ← How Claude Code was used throughout
├── ASSUMPTIONS.md          ← All assumptions documented before coding
├── AGENTIC_LOG.md          ← Real-time developer-experience friction log (13 entries)
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

> **Time estimates**: Compile/deploy timings below come straight from real measurements logged in [deploy/simplismart_notes.md](deploy/simplismart_notes.md) and [deploy/fireworks_notes.md](deploy/fireworks_notes.md). Benchmark/report/teardown timings are approximate — derived from request counts and observed per-request latencies in [report/REPORT.md](report/REPORT.md), not separately logged wall-clock runs. Treat them as planning guidance, not guarantees.

### Setup

**Prerequisites**: Python 3.11+

```bash
# 1. Clone the repo
git clone <repo-url>
cd llm-inference-benchmark

# 2. Create virtual environment and install dependencies (~1-3 min, mostly pip download time)
make setup

# 3. Copy env template and fill in your API keys
cp .env.example .env
# Edit .env: add your Simplismart and Fireworks API keys
# IMPORTANT: Verify exact model ID strings in each platform's UI before running

# 4. Activate the venv
source .venv/bin/activate

# 5. Validate config and preview the scenario plan — no API calls, no deployments (instant, < 5s)
make dry-run
```

> `make dry-run` only checks that `.env`/config are complete and prints which scenarios *would* run. It does not create any deployment or spend any money — that's a separate, explicit step below. On a fresh clone (before deployment), it will print warnings for `SIMPLISMART_BASE_URL` and `FIREWORKS_MODEL_ID` — these are expected; both fields are filled in automatically by the deploy scripts in the next step, not by you.

### Deploy

Both platforms require a **dedicated GPU endpoint** for this model (no serverless option for Gemma 3 4B). Each deploy script prints a `COST CHECKPOINT` summary (pricing, GPU, budget) and waits for you to type `yes` before it provisions anything billable.

> **Fireworks prerequisite — add a payment method before deploying.** The $5 free-credit balance is *not* sufficient to provision a dedicated GPU endpoint — Fireworks gates dedicated/H100 deployment behind having a card on file, separately from the credit balance. Skip this and `make deploy-fireworks` will fail partway through provisioning with no clear, actionable error (it looks like a transient platform issue, not a billing gate). Do this first, before running any Fireworks deploy command:
> 1. Log into [fireworks.ai](https://fireworks.ai) and open the **Dashboard**
> 2. Navigate to **Settings → Billing** (or the **Billing** section directly, depending on account type)
> 3. Click **Add payment method** and enter your card details in the payment form
> 4. Confirm the card is saved and showing as the active payment method before proceeding to `make deploy-fireworks`
>
> Simplismart had no equivalent gate for this model+GPU combination — see [AGENTIC_LOG.md](AGENTIC_LOG.md) entry "Fireworks AI — Dedicated GPU deployment requires a payment method on file, with no actionable error" for the full friction writeup.

```bash
# Simplismart: compiles the model from HuggingFace, then deploys it
# ~18 min total on a fresh compile (~15 min compile + ~3 min deploy-to-healthy)
make deploy-simplismart
# subsequent runs skip recompilation — ~3 min: make deploy-simplismart-only

# Fireworks: deploys directly via REST, no compile step — ~2-3 min (~130s provisioning + health poll)
# Requires a payment method on file — see prerequisite note above
make deploy-fireworks

# Or run both sequentially — ~20 min on a fresh Simplismart compile, ~5 min if that compile is cached
make deploy-all
```

Each script polls until the endpoint is healthy, then writes the resulting deployment IDs and inference URLs into `.env` automatically (the fields under "FILLED AUTOMATICALLY after deployment" in `.env.example`). Only once both deployments are healthy should you proceed to the benchmark step below.

### Running the Benchmark

```bash
# P0 scenarios only (90 requests across both platforms)
# ~5-10 min wall-clock across both platforms (sequential: Simplismart, then Fireworks)
make benchmark-p0

# All scenarios — P0 + P1 (130 requests across both platforms)
# ~10-20 min wall-clock — P1 adds higher-concurrency, longer-generation scenarios
make benchmark-all

# Generate comparison table and charts after benchmarking — ~10-30s (reads pre-aggregated CSVs, no API calls)
make report

# Run tests — ~5-10s (all mocked, zero real API calls)
make test
```

### CLI flags for granular control

```bash
python -m benchmark.runner --dry-run
python -m benchmark.runner --platform simplismart --priority p0
python -m benchmark.runner --platform fireworks --priority all
python -m benchmark.runner --scenarios E01,E02,E06,E07
```

### Tear Down

**Do this immediately after benchmarking** — dedicated GPU endpoints bill per hour, not per token, so leaving them up is the real cost driver (see [Estimated Costs](#estimated-costs)).

```bash
make teardown-all          # ~1-2 min total — DELETE calls plus a short poll until both report stopped
# or individually (~30-60s each):
make teardown-simplismart
make teardown-fireworks
```

`make clean` (remove `__pycache__` and runtime artifacts) is local filesystem cleanup — instant, no API calls.

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

Per-token pricing: **Simplismart $0.10/M output tokens** vs **Fireworks $0.20/M output tokens** for Gemma 3 4B — Fireworks is 2× more expensive per token. Token spend, however, was negligible at this scale; the dominant cost driver for dedicated H100 endpoints is GPU-hours, not token volume.

| GPU cost (dedicated H100, per platform) | Estimate | Actual |
|---|---|---|
| Hourly rate | ~$2.00/hr | Simplismart ~$1.99/hr · Fireworks ~$2.40/hr |
| Session cost | < $1.00 (assumes < 30 min active) | Each deployment was up for well under 30 minutes (deploy → benchmark → `make teardown-all`), so actual GPU spend stayed under $1/platform per run |

**Bottom line:** total spend across the entire project came to **≈$1.73 on Simplismart and ≈$1.70 on Fireworks** — roughly equal despite the 2× per-token price gap, because GPU-hours (not token volume) dominate the bill on dedicated endpoints. Both totals are comfortably inside the $5/platform signup credit. See [Run-to-Run Validation](report/REPORT.md#run-to-run-validation) in the report for the full per-scenario accounting.

**Hard limit**: $4.50/platform abort threshold is coded into the runner. Neither platform's $5 credit will be exceeded.

---

## Pre-committed vs Reproducible Results

| Artifact | Pre-committed? | Requires live deployment? |
|----------|---------------|--------------------------|
| `data/prompts.json` | Yes | No |
| `data/results/summary_*.csv` | Yes | No — read pre-committed |
| `data/results/*_raw.csv` | No (gitignored) | Yes |
| `report/charts/*.png` | Yes | No — regenerated from the pre-committed CSVs |
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

Claude Code (the Anthropic CLI agent) built this — repo scaffolding, module implementation, test writing, report generation, and documentation. I wrote the brief, made the platform and methodology calls, approved every spend checkpoint, and reviewed the output. [PROJECT_BRIEF.md](PROJECT_BRIEF.md) is the brief as handed to the agent before a single file existed, including notes on where the original plan (Qwen3 4B, T4 GPU, serverless-first) collided with what the platforms actually supported. [USAGE_OF_AI.md](USAGE_OF_AI.md) is the task-by-task record of what the agent did and what I changed.

Doing it agent-first wasn't just a shortcut. Handing the whole deployment to something that can only read documentation and call APIs is a good way to find out which parts of a platform genuinely work from code and which parts quietly assume a human with a browser. Most of [AGENTIC_LOG.md](AGENTIC_LOG.md) is the answer to that.

---

Built by Shreyas Athreya. Findings, corrections, and disagreement all welcome — open an issue.
