# Simplismart Deployment Notes

*Observations recorded during Phase 2 deployment.*

---

## Signup and API Key

- **Signup URL**: app.simplismart.ai
- **Account creation method**: [x] Email (Google SSO also available)
- **API key location**: Settings > API Keys — labelled "API Key" in the UI
- **Time to obtain API key from signup**: ~3 minutes (email verification required, no additional approval step)
- **Was key generation programmable via API?**: [x] No — first key requires Dashboard UI. Subsequent keys could theoretically be created programmatically but the bootstrap key must come from the browser. Documented in AGENTIC_LOG.md.
- **Scoping options on API key**: Single key per org with full access — no read-only or per-model scoping visible in the UI.
- **Note on naming**: The SDK refers to this credential as `pg_token` ("Playground Token"). The UI calls it "API Key." The inference docs call it a "Bearer token." All three names refer to the same credential. Cross-reference: AGENTIC_LOG.md entry on auth credential naming.

---

## Model Verification

- **Model searched for**: Gemma 3 4B Instruct (`google/gemma-3-4b-it`)
- **Exact model ID found in marketplace**: `google/gemma-3-4b-it` — this is the HuggingFace ID used for compilation. The inference model name (used in API calls) is `gemma-it` — returned in the deployment detail response.
- **Location of model ID**: HuggingFace model hub — Simplismart compiles directly from HuggingFace source. The inference name (`gemma-it`) is only discoverable by inspecting the `get_model_deployment()` SDK response after deployment.
- **Was model ID available in a `GET /models` API call?**: [x] No — no public `/models` list endpoint found. Model IDs must be known in advance or discovered via the marketplace UI.
- **Any ambiguity in model ID format**: Yes — the compilation ID (`google/gemma-3-4b-it`) differs from the inference model name (`gemma-it`). Using the HuggingFace ID in chat completion requests results in a model-not-found error.
- **Cross-reference**: AGENTIC_LOG.md entry "Simplismart — Dedicated deployments require a non-standard `id` header"

---

## Deployment Type

- **Deployment used**: [x] Dedicated endpoint (dedicated GPU, not shared serverless)
- **GPU type**: `nvidia-h100` (H100 80GB)
- **Autoscale configured**: `scale_to_zero_enabled=True`, `min_pod_replicas=1`, `max_pod_replicas=1`
- **Note on A100**: Initial attempt with `nvidia-a100` returned 400: "gpu a100: need 1 but only 0.0 available." H100 succeeded immediately. Cross-reference: AGENTIC_LOG.md entry "Simplismart — A100 GPU has zero quota."
- **Compile time**: ~15 minutes (Gemma 3 4B Instruct from HuggingFace on Simplismart infrastructure)
- **Deploy time after compile**: ~3 minutes to reach Healthy status
- **Endpoint URL confirmed**: `https://http.nyskemz8fi-proxy.ss-in.s9t.link` (deployment-specific subdomain, rotates per deployment)

---

## First Successful API Call

```bash
curl https://http.nyskemz8fi-proxy.ss-in.s9t.link/chat/completions \
  -H "Authorization: Bearer $SIMPLISMART_API_KEY" \
  -H "id: $SIMPLISMART_DEPLOYMENT_ID" \
  -H "Content-Type: application/json" \
  -d '{"model": "gemma-it", "messages": [{"role": "user", "content": "Say hello"}], "max_tokens": 10, "stream": true}'
```

- **Time from account creation to first successful inference**: ~20 minutes (dominated by compile time)
- **Auth errors before success**: Yes — first inference attempts failed because the `id: <deployment_uuid>` header was missing. This header is not mentioned in the quickstart. It was discovered by reading the `api_details.curl` field in the `get_model_deployment()` SDK response. Cross-reference: AGENTIC_LOG.md entry "Simplismart — Dedicated deployments require a non-standard `id` header."

---

## Friction Encountered

*(Cross-reference each item to an AGENTIC_LOG.md entry)*

- [x] Signup required UI steps not automatable — first API key must come from Dashboard browser session
- [x] Model ID not available via API — no `/models` list endpoint; inference name differs from HuggingFace compile ID
- [x] Deployment API returns 500 but silently creates the deployment — AGENTIC_LOG.md entry "Simplismart — Deployment API returns 500 but silently creates the deployment"
- [x] Required non-standard `id` header on inference requests — AGENTIC_LOG.md entry "Simplismart — Dedicated deployments require a non-standard `id` header on every inference request"
- [x] A100 listed as valid GPU but has zero quota — AGENTIC_LOG.md entry "Simplismart — A100 GPU has zero quota despite being listed as a valid accelerator"
- [x] Two separate base URLs for management vs. inference APIs, unexplained in docs — AGENTIC_LOG.md entry "Simplismart — Two different base URLs for two different API surfaces"
- [x] Auth credential has three different names across docs (PG Token, JWT Token, API Key) — AGENTIC_LOG.md entry "Simplismart — Auth credential has two different names across docs"

---

## Screenshots to Capture

*(Actual images to be added to `report/screenshots/` manually)*

- [ ] Marketplace page showing Gemma 3 4B model listing (`google/gemma-3-4b-it`)
- [ ] Model detail page showing exact API model ID
- [ ] API key settings page
- [ ] Deployment configuration page showing H100 and scale-to-zero
- [ ] First successful API response in terminal (with `id` header visible in curl command)

---

## Summary

- **Overall deployment experience (1–5)**: 2/5
- **Key friction points**:
  1. The `id` header requirement is completely undocumented in the quickstart — any developer using a standard OpenAI client will get silent failures with no helpful error message
  2. Deployment creation returns 500 on success — makes retry logic dangerous (duplicate deployments) and recovery non-obvious
  3. Two separate API domains for management vs. inference with no explanation in docs — a developer who reads the SDK quickstart will have the wrong base URL for chat completions
- **What worked well**: Compile-from-HuggingFace flow is a strong product differentiator; once the `id` header was discovered, inference was fast and stable (100% success rate, ~152ms warm TTFT); scale-to-zero worked correctly
- **Time to first token from signup**: ~20 minutes (dominated by ~15 min compile + 3 min health check + debugging the `id` header)
