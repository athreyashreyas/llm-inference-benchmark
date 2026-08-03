# Assumptions

Written down before any code was, and added to as new assumptions surfaced during the build. Where reality later contradicted one, the correction is logged in [AGENTIC_LOG.md](AGENTIC_LOG.md) rather than quietly edited in here.

---

## 1. Model Choice

**Deployed: Gemma 3 4B Instruct** (`google/gemma-3-4b-it`)

Rationale:

1. Available on both Simplismart and Fireworks AI as dedicated H100 deployments. Confirmed deployable on both platforms before committing to the model choice.

2. Smallest cost-effective model at $0.10/1M output tokens — most budget-safe for a $5 credit ceiling per platform.

3. 4B parameters (~8GB VRAM). Fits comfortably on H100 80GB (80GB VRAM) with 72GB headroom. No quantization required.

4. Current-generation model (2025 release). Relevant for a platform positioning itself on inference speed for modern open-weight models.

5. Apache 2.0 license. No commercial restrictions.

**Llama 3.1 8B explicitly excluded**: Simplismart's own blog provides a full deployment guide for it, reducing deployment discovery value.

**GPU**: NVIDIA H100 80GB (dedicated, 1× per platform). A100 was initially considered but has zero quota on Simplismart (documented in AGENTIC_LOG.md). H100 confirmed available and used on both platforms.

---

## 2. Deployment Type

Dedicated GPU endpoints on both platforms (serverless was not available for this model+GPU combination). Scale-to-zero configured on both: `min_replicas=0` on Fireworks, `scale_to_zero_enabled=True` on Simplismart. GPU billing stops when idle.

---

## 3. Scale-to-Zero

If dedicated deployment is required, min_replicas=0 is configured so GPU billing stops when idle. If autoscale is unavailable on the platform, the deployment is paused manually immediately after benchmarking completes, and this constraint is logged as a product finding.

---

## 4. Benchmark Scope

Approximately 280 total requests across both platforms across all scenarios (P0 + P1). P0-only run is approximately 180 requests (90 per platform). A few hundred requests is enough to surface the differences that matter here and keeps the run inside the credit budget. Results are indicative, not statistically definitive — a production-grade study would require thousands of samples with controlled network conditions.

---

## 5. TTFT Measurement

Time-to-first-token (TTFT) measurement requires streaming (stream=True). If streaming is unavailable on either platform, the benchmark falls back to E2E latency only with this explicitly noted as a platform limitation in AGENTIC_LOG.md and the final report.

---

## 6. Network Conditions

Both platforms are tested from the same machine and geographic region. Network latency differences between platforms are not controlled for — platform-side differences in cold start time, routing, and CDN proximity may influence results. Results should be interpreted as "end-user experience from this region" rather than "raw inference speed."

---

## 7. Model IDs

Model ID strings are verified in each platform's UI before any API call is made. Exact verified strings are documented in `deploy/simplismart_notes.md` and `deploy/fireworks_notes.md`. Wrong model IDs cause silent 404s or unexpected routing — this verification step is non-negotiable.

---

## 8. Budget

$5 free credits on each platform. Total API benchmark cost estimated under $0.10. Dedicated H100 GPU-hours are the dominant cost driver; both deployments ran under 30 minutes total. Hard abort at $4.50 per platform to leave headroom. Total spend ceiling: $5 per platform, not negotiable.

---

## 9. Concurrency Model

Concurrent requests are launched with asyncio and a Semaphore. "Concurrency=5" means up to 5 requests in-flight simultaneously, not 5 sequential batches. This tests real concurrent load on shared inference infrastructure, which is the relevant scenario for agentic applications.

---

## 11. Token Counting

Input and output token counts are taken from the API response `usage` field where available. If the `usage` field is absent (some streaming implementations omit it), token counts are approximated by splitting on whitespace (input) and counting streamed chunks (output). Any approximation is noted in the raw results.

---

## 12. Competitor Selection (Fireworks AI)

Fireworks AI was selected as the competitor platform for the following reasons:
- Dedicated H100 deployment confirmed available for Gemma 3 4B Instruct (`accounts/fireworks/models/gemma-3-4b-it`)
- OpenAI-compatible API, enabling the same benchmark code with only base URL and key swapped
- Developer-focused positioning, making it a natural comparison for Simplismart's target market
- $5 free credits on signup — sufficient for this benchmark at $0.10/1M output tokens for Gemma 3 4B
- Strong reputation for high-throughput inference, making it a credible competitive reference point
