# Fireworks AI Deployment Notes

*Observations recorded during Phase 2 deployment.*

---

## Signup and API Key

- **Signup URL**: fireworks.ai
- **Account creation method**: [x] Email (Google SSO also available)
- **API key location**: Dashboard > API Keys
- **Time to obtain API key from signup**: ~2 minutes (no email verification required beyond OAuth)
- **Was key generation programmable via API?**: [x] No for the first key — the bootstrap key must be created via Dashboard UI. The API does expose a `POST /v1/accounts/{id}/users/{id}/apiKeys` endpoint, but it requires Bearer auth with an existing key. Cross-reference: AGENTIC_LOG.md entry "Fireworks AI — API key creation requires existing credentials."
- **Scoping options on API key**: Full-access keys visible in Dashboard; no read-only or per-model scoping in the standard UI.
- **Payment method requirement (blocking)**: The $5 free-credit balance covers serverless/light usage but is **not** sufficient to provision a *dedicated* GPU endpoint — Fireworks gates dedicated/H100 deployment behind having a card on file (Dashboard → Billing). There is no clear, actionable error surfaced for this; the deploy attempt simply fails partway through provisioning rather than returning something like "add a payment method to deploy dedicated endpoints." A payment method had to be added *before* `deploy_fireworks.py` could succeed. Cross-reference: AGENTIC_LOG.md entry "Fireworks AI — Dedicated GPU deployment requires a payment method on file, with no actionable error."
- **Steps to add a payment method (do this before any dedicated-deployment attempt)**:
  1. Log into the Fireworks Dashboard at fireworks.ai
  2. Navigate to Settings → Billing (or the Billing section directly)
  3. Click "Add payment method" and enter card details in the payment form
  4. Confirm the card shows as the active payment method, then re-run the deploy script — it succeeds immediately with no code changes once this is in place

---

## Model Verification

- **Model searched for**: Gemma 3 4B Instruct
- **Exact model ID found in model library**: `accounts/fireworks/models/gemma-3-4b-it`
- **Location of model ID**: Discovered programmatically via `GET /v1/accounts/fireworks/models?pageSize=200` — the model ID appears in the `name` field of the model list response. This is a genuine strength: Fireworks exposes a machine-readable models list.
- **Was model ID available via `GET /v1/models`?**: [x] Yes — `GET /v1/accounts/fireworks/models` returns all available models with their full path IDs.
- **Any ambiguity in model ID format**: Minor — needed to distinguish `gemma-3-4b-it` (instruct, correct) from `gemma-3-4b` (base) and other Gemma variants in the list. An initial attempt with `gemma-3-4b-instruct` returned 404 — the correct suffix is `-it`, not `-instruct`.
- **Cross-reference**: AGENTIC_LOG.md entry "Fireworks AI — H100 returns 404 for some models but not others"

---

## Deployment Type

- **Deployment used**: [x] Dedicated endpoint (no serverless option for Gemma 3 4B on H100)
- **GPU type**: `NVIDIA_H100_80GB`
- **Autoscale configured**: `minReplicaCount=0`, `maxReplicaCount=1`, `autoscalingPolicy.scaleToZeroWindow=300s` (5 min idle window)
- **Note on shape discovery**: `GET /v1/accounts/fireworks/deploymentShapeVersions` returns 404 for all accounts — the documented deployment shape approach is unusable. Deployment succeeded via direct `acceleratorType: NVIDIA_H100_80GB` in the POST body. Cross-reference: AGENTIC_LOG.md entry "Fireworks AI — `deploymentShapeVersions` endpoint returns 404."
- **Deploy time**: ~130 seconds from POST to READY state
- **Endpoint URL**: `https://api.fireworks.ai/inference/v1` (shared base URL; model routed by inference model ID)
- **Inference model ID**: `accounts/athreya-shreyas-np8t/deployments/tyojayoy`

---

## First Successful API Call

```bash
curl https://api.fireworks.ai/inference/v1/chat/completions \
  -H "Authorization: Bearer $FIREWORKS_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model": "accounts/athreya-shreyas-np8t/deployments/tyojayoy",
       "messages": [{"role": "user", "content": "Say hello"}],
       "max_tokens": 10, "stream": true}'
```

- **Time from account creation to first successful inference**: ~10 minutes (including model ID discovery and 130s deployment time)
- **Auth errors before success**: None — standard Bearer auth worked immediately. No custom headers required.
- **Note on DELETE**: Teardown via `DELETE /v1/accounts/{id}/deployments/{id}` returned 400 "recent inference requests" without the `?ignoreChecks=true` query parameter. Adding this param resolved it. Not documented.

---

## Friction Encountered

*(Cross-reference each item to an AGENTIC_LOG.md entry)*

- [x] Signup required UI steps not automatable — first API key must come from Dashboard browser session — AGENTIC_LOG.md entry "Fireworks AI — API key creation requires existing credentials"
- [x] Dedicated GPU deployment silently requires a payment method on file (separate from free-credit balance), surfaced as an opaque provisioning failure with no actionable error — AGENTIC_LOG.md entry "Fireworks AI — Dedicated GPU deployment requires a payment method on file, with no actionable error"
- [x] `deploymentShapeVersions` endpoint 404 — documented deployment shape path unusable — AGENTIC_LOG.md entry "Fireworks AI — `deploymentShapeVersions` endpoint returns 404"
- [x] H100 availability is model-dependent with no programmatic pre-check — AGENTIC_LOG.md entry "Fireworks AI — H100 returns 404 for some models but not others"
- [x] Teardown DELETE blocked without `?ignoreChecks=true` — not documented
- [ ] Streaming response format differed from OpenAI spec — No, Fireworks streaming was fully OpenAI-compatible

---

## Screenshots to Capture

*(Actual images to be added to `report/screenshots/` manually)*

- [ ] Model library page showing Gemma 3 4B listing
- [ ] Model detail page showing exact API model ID (`accounts/fireworks/models/gemma-3-4b-it`)
- [ ] API key settings page (Dashboard)
- [ ] First successful API response in terminal

---

## Comparison with Simplismart

| Dimension | Simplismart | Fireworks AI |
|-----------|------------|--------------|
| Time to first API key | ~3 min (UI only) | ~2 min (UI only) |
| Time to first inference | ~20 min (15 min compile + debug) | ~10 min (130s deploy + model ID lookup) |
| Model ID discoverability | Not via API — requires marketplace UI or SDK compile response | Yes — `GET /v1/accounts/fireworks/models` returns full model list |
| Non-standard auth requirements | Yes — `id: <uuid>` header required on every request | No — standard Bearer auth only |
| Docs clarity | 2/5 — two base URLs unexplained, inference model name differs from compile ID, `id` header undocumented | 4/5 — API reference is complete; shape discovery 404 is the main gap |
| Serverless availability | No — dedicated GPU required for Gemma 3 4B | No — dedicated GPU required for Gemma 3 4B |
| OpenAI compatibility | Partial — requires custom `id` header; otherwise compatible | Full — drop-in compatible, no custom headers |
| Scale-to-zero | Yes — `scale_to_zero_enabled=True` | Yes — `minReplicaCount=0`, 5 min window |
| Deploy time | ~18 min (compile + deploy) | ~2 min (no compile step) |

---

## Summary

- **Overall deployment experience (1–5)**: 4/5
- **Key friction points**:
  1. Dedicated GPU deployment silently requires a payment method on file — the $5 free-credit balance alone is not enough, and the failure surfaces as an opaque provisioning error rather than "add a payment method"
  2. `deploymentShapeVersions` endpoint is documented but returns 404 — the recommended deployment path is a dead end; must fall back to `acceleratorType` and hope the GPU is available
  3. H100 availability is model-dependent and not discoverable programmatically — requires trial and error or UI inspection
  4. DELETE blocked without `?ignoreChecks=true` — teardown fails silently without this undocumented param
- **What worked well**: Fast deployment (130s vs 15 min compile on Simplismart); standard OpenAI-compatible inference with no custom headers; machine-readable model list via GET /models; clear deployment status polling response with `replicaStats` breakdown
- **Time to first token from signup**: ~10 minutes
