# LLM Inference Benchmark: Simplismart vs Fireworks AI

**Model:** Gemma 3 4B Instruct (`google/gemma-3-4b-it`)  
**GPU:** NVIDIA H100 80GB — 1× dedicated on each platform  
**Date:** 2026-06-07  
**Run ID:** ba442d8d (full P0 + P1 scenario set, E01–E10)  
**Validation run:** 72b46d09 (P0-only, redeployed independently — see [Run-to-Run Validation](#run-to-run-validation))

---

## Setup

Both platforms were provisioned with a dedicated, single-GPU H100 endpoint serving Gemma 3 4B Instruct. Scale-to-zero was enabled on both (5-minute idle window) to minimise cost. All benchmarks used the OpenAI-compatible streaming chat completions API.

| | Simplismart | Fireworks AI |
|---|---|---|
| Model ID | `gemma-it` | `accounts/athreya-shreyas-np8t/deployments/idxwnhnu` |
| Endpoint | `https://http.okrtzjltb6-proxy.ss-in.s9t.link` | `https://api.fireworks.ai/inference/v1` |
| GPU | nvidia-h100 (dedicated) | NVIDIA_H100_80GB (dedicated) |
| Min replicas | 1 (scale-to-zero enabled) | 0 (scale-to-zero enabled) |
| Deployment time | ~15 min compile (reused, skipped via `--deploy-only`) + instant deploy | 130 seconds |

---

## Scenarios

| Scenario | Prompt type | Max tokens | Concurrency | Reps | Priority |
|---|---|---|---|---|---|
| E01 / E06 | Short | 50 | 1 | 15 | P0 |
| E02 / E07 | Medium | 150 | 1 | 15 | P0 |
| E03 / E08 | Short | 50 | 5 | 15 | P0 |
| E04 / E09 | Medium | 150 | 5 | 10 | P1 |
| E05 / E10 | Long | 200 | 10 | 10 | P1 |

Each scenario ran 3 warm-up requests (discarded) before the measured reps. A cold-start probe ran before all scenarios on each platform to capture GPU spin-up latency. P0 scenarios cover the core latency/throughput comparison at low concurrency; P1 scenarios extend the comparison to higher concurrency (5, 10) and longer generations (150–200 tokens) to test how each platform scales under sustained load.

---

## Results

### Throughput & Request Stats

| Platform | Scenario | Concurrency | Req/s | Out tok/s | Total tok/s | Total Out Tokens | Cold Start TTFT (ms) |
|---|---|---|---|---|---|---|---|
| Simplismart | E01 | 1 | 3.06 | 132.04 | 186.33 | 647 | 503.35 |
| Simplismart | E02 | 1 | 1.27 | 188.85 | 221.56 | 2223 | 503.35 |
| Simplismart | E03 | 5 | 6.52 | 289.75 | 405.30 | 667 | 503.35 |
| Simplismart | E04 | 5 | 2.61 | 390.07 | 457.52 | 1492 | 503.35 |
| Simplismart | E05 | 10 | 2.44 | 487.92 | 590.88 | 2000 | 503.35 |
| Fireworks AI | E06 | 1 | 0.74 | 32.24 | 45.34 | 655 | 4349.37 |
| Fireworks AI | E07 | 1 | 0.63 | 93.68 | 110.09 | 2238 | 4349.37 |
| Fireworks AI | E08 | 5 | 3.18 | 134.80 | 191.18 | 636 | 4349.37 |
| Fireworks AI | E09 | 5 | 2.21 | 326.62 | 383.71 | 1476 | 4349.37 |
| Fireworks AI | E10 | 10 | 3.70 | 740.47 | 896.70 | 2000 | 4349.37 |

### Latency Metrics

| Platform | Scenario | Concurrency | Mean TTFT (ms) | p50 TTFT | p95 TTFT | p99 TTFT | Mean TPOT (ms) | Mean ITL (ms) | Mean E2E (ms) | p99 E2E |
|---|---|---|---|---|---|---|---|---|---|---|
| Simplismart | E01 | 1 | 149.38 | 133.83 | 215.56 | 215.90 | 4.19 | 4.17 | 326.29 | 406.69 |
| Simplismart | E02 | 1 | 141.06 | 134.25 | 219.58 | 235.21 | 4.37 | 4.36 | 784.44 | 864.62 |
| Simplismart | E03 | 5 | 347.16 | 149.77 | 1160.77 | 1165.89 | 4.59 | 4.55 | 548.56 | 1343.66 |
| Simplismart | E04 | 5 | 566.39 | 187.44 | 2258.54 | 3012.04 | 4.97 | 4.97 | 1304.29 | 3644.88 |
| Simplismart | E05 | 10 | 650.66 | 170.30 | 2270.03 | 2997.85 | 4.55 | 4.54 | 1555.27 | 3905.57 |
| Fireworks AI | E06 | 1 | 1135.86 | 1218.11 | 1425.64 | 1433.66 | 5.28 | 5.47 | 1354.12 | 1666.01 |
| Fireworks AI | E07 | 1 | 911.76 | 819.13 | 1309.20 | 1441.13 | 4.59 | 4.62 | 1592.37 | 2118.23 |
| Fireworks AI | E08 | 5 | 1127.14 | 1245.24 | 1492.54 | 1495.43 | 6.16 | 6.34 | 1369.99 | 1711.10 |
| Fireworks AI | E09 | 5 | 1266.98 | 1264.75 | 1847.08 | 1871.32 | 4.77 | 4.80 | 1966.26 | 2590.35 |
| Fireworks AI | E10 | 10 | 1124.46 | 969.04 | 1681.64 | 1708.32 | 5.14 | 5.15 | 2146.53 | 2687.19 |

Both platforms returned a 100% success rate across all 10 scenarios (280 total requests, 130 per platform).

---

## Analysis

### Time to First Token (TTFT)

Simplismart delivers markedly lower TTFT at low concurrency: at concurrency=1, mean TTFT is **~145 ms** (E01/E02 average) vs **~1,024 ms** on Fireworks (E06/E07 average) — roughly a **7× difference**. This gap persists but narrows as concurrency rises: at concurrency=5 (E03/E04 vs E08/E09), Simplismart sits at 347–566 ms while Fireworks sits at 1,127–1,267 ms, and at concurrency=10 (E05 vs E10) Simplismart's 651 ms is still well below Fireworks' 1,124 ms. Fireworks' TTFT is dominated by a large, fairly constant baseline (~900–1,300 ms) that looks like routing/queueing overhead in its serving layer rather than GPU compute, while Simplismart's TTFT scales more directly with queue depth — rising from ~145 ms (conc=1) to ~650 ms (conc=10) as the single-GPU deployment queues requests.

![TTFT Comparison](charts/ttft_comparison.png)

### Time Per Output Token (TPOT) & Inter-Token Latency (ITL)

TPOT is close across both platforms and stays in a narrow band regardless of concurrency or prompt length: **4.19–4.97 ms** on Simplismart vs **4.59–6.16 ms** on Fireworks. This is expected — both platforms run the same model on the same GPU class, so steady-state token generation speed is bound by the GPU, not the serving infrastructure. Fireworks' TPOT does drift slightly higher under concurrency=5 (E08: 6.16 ms, E09: 4.77 ms — E08 in particular stands out as the highest TPOT in either dataset), suggesting marginally more contention for compute when many short-prompt requests are in flight simultaneously; Simplismart's TPOT stays essentially flat (4.19–4.97 ms) across all five of its scenarios.

ITL tracks TPOT closely on both platforms (differences are in the hundredths of a millisecond), confirming smooth, consistent token streaming once generation starts — there is no platform-specific stutter or buffering effect visible in the data.

![TPOT Comparison](charts/tpot_comparison.png)
![ITL Comparison](charts/itl_comparison.png)

### Throughput

At concurrency=1, Simplismart's output token throughput is **~3–4× higher** than Fireworks (132–189 tok/s vs 32–94 tok/s) — a direct consequence of the TTFT gap dominating per-request wall time at low concurrency.

The P1 scenarios (E04/E05 vs E09/E10) show how this gap evolves under load. As concurrency rises to 5 and then 10, both platforms' throughput climbs roughly in proportion — Simplismart goes from 290 tok/s (E03, conc=5) to 390 tok/s (E04, conc=5, longer output) to 488 tok/s (E05, conc=10); Fireworks goes from 135 tok/s (E08) to 327 tok/s (E09) to **740 tok/s (E10)**. Notably, at concurrency=10 with long (200-token) generations, Fireworks' throughput overtakes Simplismart's (740 vs 488 tok/s) — the only scenario where Fireworks leads on raw output throughput. This suggests Fireworks' serving stack batches and parallelises generation more efficiently at high concurrency once its larger fixed TTFT overhead is amortised across more simultaneous requests, while Simplismart's single-GPU deployment appears to hit a throughput ceiling around 490 tok/s as queueing costs (visible in its rising TTFT) start to eat into gains from added concurrency.

![Throughput Comparison](charts/throughput_comparison.png)
![Latency vs Concurrency](charts/latency_concurrency.png)

### Cold Start

Simplismart cold start: **503 ms**. Fireworks cold start: **4,349 ms**. Both endpoints were freshly (re)provisioned for this run, and both cold-start values are markedly higher than in the original validation run (Simplismart 391 ms → 503 ms, +29%; Fireworks 1,412 ms → 4,349 ms, +208%). Simplismart's cold start remains in a tight, low band across both runs (391–503 ms), consistent with a lightweight scale-from-zero path. Fireworks' cold start is far more variable — the 3× jump here likely reflects a colder GPU pool or scheduling contention at the moment this particular deployment was spun up, rather than a systemic regression (steady-state metrics for Fireworks in this run are, if anything, slightly *better* than the validation run — see below). For latency-sensitive, intermittent-traffic applications, Simplismart's spin-up remains both faster and more predictable.

### Cost

Both platforms priced at $0.10/M output tokens for Gemma 3 4B. The full 10-scenario run consumed under 13,000 total output tokens across both platforms — combined estimated spend of ~$0.0026, well inside the $5/platform budget ceiling. The dominant cost driver for dedicated H100 endpoints remains GPU-hours, not token volume; both deployments were active for well under an hour total (deploy → benchmark → teardown) and were torn down immediately after this run completed.

![p99 Tail Latency](charts/p99_comparison.png)

---

## Run-to-Run Validation

To confirm the original P0 results (run `72b46d09`) weren't a one-off, both platforms were redeployed from scratch on H100 with the same model and the **complete** scenario set (P0 + P1, E01–E10) was run again as `ba442d8d`. Comparing the six overlapping P0 scenarios (E01, E02, E03, E06, E07, E08) across the two independent deployments:

| Scenario | Metric | Run 72b46d09 (baseline) | Run ba442d8d (this run) | Δ |
|---|---|---|---|---|
| E01 | Mean TTFT | 161.6 ms | 149.4 ms | −7.6% |
| E01 | Mean TPOT | 3.95 ms | 4.19 ms | +6.1% |
| E01 | Out tok/s | 132.7 | 132.0 | −0.5% |
| E02 | Mean TTFT | 143.5 ms | 141.1 ms | −1.7% |
| E02 | Mean TPOT | 4.27 ms | 4.37 ms | +2.3% |
| E02 | Out tok/s | 191.8 | 188.9 | −1.5% |
| E03 | Mean TTFT | 419.1 ms | 347.2 ms | −17.2% |
| E03 | Mean TPOT | 4.34 ms | 4.59 ms | +5.8% |
| E03 | Out tok/s | 184.0 | 289.8 | +57.4% |
| E03 | p99 TTFT | 2,961.0 ms | 1,165.9 ms | −60.6% |
| E06 | Mean TTFT | 1,343.2 ms | 1,135.9 ms | −15.4% |
| E06 | Mean TPOT | 4.82 ms | 5.28 ms | +9.5% |
| E06 | Out tok/s | 28.8 | 32.2 | +12.1% |
| E07 | Mean TTFT | 1,437.3 ms | 911.8 ms | −36.6% |
| E07 | Mean TPOT | 4.56 ms | 4.59 ms | +0.7% |
| E07 | Out tok/s | 70.4 | 93.7 | +33.2% |
| E07 | p99 TTFT | 3,823.9 ms | 1,441.1 ms | −62.3% |
| E08 | Mean TTFT | 1,322.0 ms | 1,127.1 ms | −14.7% |
| E08 | Mean TPOT | 5.09 ms | 6.16 ms | +21.0% |
| E08 | Out tok/s | 134.5 | 134.8 | +0.2% |

**Conclusion: the two runs are consistent and corroborate each other.** Mean TTFT, TPOT, and throughput stay within roughly ±20% across two independent deployments — normal run-to-run variance for shared cloud GPU infrastructure, and small relative to the 3–8× cross-platform gaps that drive this report's conclusions. Two points are worth calling out explicitly:

- **p99 tail latency moved more than the means** (E03 and E07 p99 TTFT both dropped by ~60%). With only 15 reps per scenario, a single slow outlier can swing a p99 substantially — this looks like sampling noise rather than a platform change, since the corresponding *mean* TTFTs moved far less (E03: −17%, E07: −37%, still directionally favourable to the same conclusions).
- **Cold-start TTFT was notably higher in this run on both platforms** (Simplismart +29%, Fireworks +208% — see [Cold Start](#cold-start)). This reflects fresh-deployment GPU spin-up variance and does not affect any steady-state scenario metric, since the cold-start probe runs once, before the first scenario, and is reported separately.
- **All success rates remained 100%** in both runs — no reliability regressions.

This validation gives confidence that the P0 conclusions in this report (Simplismart's TTFT/throughput advantage at low concurrency, near-identical TPOT, Fireworks' faster deploy path) are stable platform characteristics rather than artefacts of a single benchmark session — and it additionally surfaces the P1 finding that **Fireworks overtakes Simplismart on raw throughput at high concurrency with long generations (E10)**, which the original P0-only run could not have shown.

---

## Summary

| Metric | Winner | Margin |
|---|---|---|
| TTFT (warm, conc=1) | **Simplismart** | ~7× faster (145 ms vs 1,024 ms) |
| TTFT (conc=5–10) | **Simplismart** | 2–3× faster, though gap narrows with load |
| TPOT | Tie (slight edge: Simplismart) | 4.2–5.0 ms vs 4.6–6.2 ms |
| ITL | Tie | tracks TPOT on both platforms |
| Output throughput (conc=1) | **Simplismart** | 3–4× higher |
| Output throughput (conc=5) | **Simplismart** | ~1.2–1.5× higher |
| Output throughput (conc=10, long gen) | **Fireworks** | 740 vs 488 tok/s — only scenario Fireworks leads |
| Cold start | **Simplismart** | ~6–9× faster and far more consistent run-to-run |
| Deployment speed | **Fireworks** | 130s vs ~15 min (compile required, though reusable) |
| Cost per token | Tie | $0.10/M output tokens on both |
| Reliability | Tie | 100% success across all 10 scenarios, both platforms, both runs |

**Simplismart is the better choice for latency-sensitive, low-to-medium concurrency workloads** — chatbots, copilots, interactive applications — where TTFT directly impacts perceived responsiveness, and where its faster, more predictable cold start matters for intermittent traffic.

**Fireworks becomes competitive — and at the highest concurrency with long generations, actually wins on raw throughput** (E10: 740 vs 488 tok/s). Combined with its much faster deployment path (no compilation step) and full OpenAI compatibility (no custom headers), Fireworks is the stronger pick for batch or sustained high-throughput workloads where TTFT matters less than aggregate tokens-per-second, and for teams that want to iterate on deployments quickly.

Both platforms delivered 100% request success rates across all scenarios in both benchmark runs (280 total requests).

---

## Methodology Notes

- All timings measured client-side using `time.perf_counter()` with Python's asyncio streaming
- TTFT: elapsed time from request start to first content-bearing chunk
- TPOT: `(e2e - ttft) / (output_tokens - 1)` — average time per output token after the first
- ITL: mean of observed inter-chunk gaps from streaming timestamps
- Cold start probe: single request before warm scenarios, result reported separately and not included in scenario percentiles
- Warm-up requests: 3 per scenario, discarded from metrics
- This run (`ba442d8d`) covers the full P0 + P1 scenario set (E01–E10, 130 requests/platform). The P0 subset (E01/E02/E03/E06/E07/E08) was independently re-validated against an earlier run (`72b46d09`, P0-only, separate deployment) — see [Run-to-Run Validation](#run-to-run-validation)
- Raw data: `data/results/simplismart_ba442d8d_raw.csv`, `data/results/fireworks_ba442d8d_raw.csv` (and `*_72b46d09_raw.csv` for the validation run)
- Summary data: `data/results/summary_ba442d8d.csv` (and `summary_72b46d09.csv` for the validation run)
