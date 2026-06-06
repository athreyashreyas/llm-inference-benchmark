# Assumptions

All assumptions documented before any code was written. Added to as assumptions emerge during development.

---

## 1. Model Choice

**Deployed: Qwen3 14B Instruct**

Original target was Qwen3 4B. Switched to Qwen3 14B after discovering Qwen3 4B is listed on Simplismart's pricing page but absent from the marketplace — no deployable endpoint available. Qwen3 14B was the smallest Qwen3 model actually present in Simplismart's marketplace.

Rationale for Qwen3 14B:

1. Only Qwen3 variant actually available in Simplismart's marketplace at time of benchmarking. The pricing page listing of Qwen3 4B was not reflected in deployable inventory — a product gap documented in AGENTIC_LOG.md.

2. Available on Fireworks as dedicated-only deployment (`accounts/fireworks/models/qwen3-14b`, status: Ready). Serverless not supported for this model on Fireworks, which aligns with the dedicated GPU deployment requirement.

3. 14B parameters: ~28GB VRAM in BF16. Fits comfortably on A100 80GB (80GB VRAM) with 52GB headroom. No quantization required.

4. Qwen3 14B retains the hybrid thinking architecture (fast-answer vs. chain-of-thought) of the Qwen3 family, preserving the latency benchmarking value of the original model choice.

5. Apache 2.0 license. No commercial restrictions.

6. Current-generation model (2025 release). Relevant for a platform positioning itself on inference speed for modern open-weight models.

**Llama 3.1 8B explicitly excluded**: Simplismart's own blog provides a full deployment guide for it, reducing deployment discovery value.

**Original Qwen3 4B rationale retained for reference**: cheaper ($0.10/1M vs estimated higher for 14B), smaller GPU footprint, but unavailable in Simplismart marketplace at time of task execution.

---

## 2. Deployment Type

Shared/serverless endpoints preferred on both platforms. Zero idle cost. No dedicated GPU provisioning unless serverless is unavailable for the chosen model.

If dedicated deployment is required: T4 GPU ($1.20/hr on Simplismart) with autoscale min_replicas=0, max_replicas=1. GPU billing stops when idle. Paused manually if autoscale is unavailable.

---

## 3. Scale-to-Zero

If dedicated deployment is required, min_replicas=0 is configured so GPU billing stops when idle. If autoscale is unavailable on the platform, the deployment is paused manually immediately after benchmarking completes, and this constraint is logged as a product finding.

---

## 4. Benchmark Scope

Approximately 280 total requests across both platforms across all scenarios (P0 + P1). P0-only run is approximately 180 requests (90 per platform). This is illustrative per the task specification ("few hundreds"). Results are indicative, not statistically definitive. A production-grade study would require thousands of samples with controlled network conditions.

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

$5 free credits on each platform. Total API benchmark cost estimated under $0.10. If dedicated GPU usage is required, estimated under $1.00 at $1.20/hr for a T4 GPU. Hard abort at $4.50 per platform to leave headroom. Total spend ceiling: $5 per platform, not negotiable.

---

## 9. Qwen3 Thinking Mode

Qwen3 4B supports both "thinking" (chain-of-thought, `/think` tag) and "non-thinking" (fast-answer) modes. All benchmark requests use non-thinking mode (no `/think` tag in prompts, temperature=0.7) for consistent latency measurement. Mixing modes would make latency comparison meaningless.

---

## 10. Concurrency Model

Concurrent requests are launched with asyncio and a Semaphore. "Concurrency=5" means up to 5 requests in-flight simultaneously, not 5 sequential batches. This tests real concurrent load on shared inference infrastructure, which is the relevant scenario for agentic applications.

---

## 11. Token Counting

Input and output token counts are taken from the API response `usage` field where available. If the `usage` field is absent (some streaming implementations omit it), token counts are approximated by splitting on whitespace (input) and counting streamed chunks (output). Any approximation is noted in the raw results.

---

## 12. Competitor Selection (Fireworks AI)

Fireworks AI was selected as the competitor platform for the following reasons:
- Explicit serverless support for the Qwen3 model family (confirmed from their blog)
- OpenAI-compatible API, enabling the same benchmark code with only base URL and key swapped
- Developer-focused positioning, making it a natural comparison for Simplismart's target market
- $5 free credits on signup — sufficient for this benchmark at $0.20/1M tokens for 4B-16B models
- Strong reputation for high-throughput inference, making it a credible competitive reference point
