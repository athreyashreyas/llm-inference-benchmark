# Fireworks AI Deployment Notes

*Template populated during Phase 1. Real observations added during Phase 2.*

---

## Signup and API Key

- **Signup URL**: fireworks.ai
- **Account creation method**: [ ] Email / [ ] Google / [ ] GitHub
- **API key location**: Dashboard > API Keys
- **Time to obtain API key from signup**: [fill in during Phase 2]
- **Was key generation programmable via API?**: [ ] Yes / [ ] No (document in AGENTIC_LOG.md if No)
- **Scoping options on API key**: [describe — e.g., read-only, full-access, per-model]

---

## Model Verification

- **Model searched for**: Gemma 3 4B Instruct
- **Exact model ID found in model library**: `accounts/fireworks/models/gemma-3-4b-it`
- **Location of model ID**: [e.g., Model Library > Model card > "API ID" field]
- **Was model ID available via `GET /v1/models`?**: [ ] Yes / [ ] No
- **Any ambiguity in model ID format**: [describe — e.g., instruction-tuned vs base variant naming]
- **Cross-reference**: AGENTIC_LOG.md entry #[N]

---

## Deployment Type

- **Deployment used**: [x] Serverless (default — no provisioning required)
- **Scale-to-zero**: [x] Built-in — no idle GPU cost
- **Endpoint URL**: https://api.fireworks.ai/inference/v1

---

## First Successful API Call

```bash
# curl test command used:
# curl https://api.fireworks.ai/inference/v1/chat/completions \
#   -H "Authorization: Bearer $FIREWORKS_API_KEY" \
#   -H "Content-Type: application/json" \
#   -d '{"model": "<MODEL_ID>", "messages": [{"role": "user", "content": "Say hello"}], "max_tokens": 10}'

# Actual response (fill in during Phase 2):
```

- **Time from signup to first successful API response**: [fill in]
- **Any auth errors before success**: [describe]

---

## Friction Encountered

*(Cross-reference each item to an AGENTIC_LOG.md entry)*

- [ ] Signup required UI steps not automatable — LOG ENTRY #[ ]
- [ ] Model ID not available via API — LOG ENTRY #[ ]
- [ ] Streaming response format differed from OpenAI spec — LOG ENTRY #[ ]
- [ ] Rate limit headers absent or non-standard — LOG ENTRY #[ ]
- [ ] Other: [describe]

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
| Time to first API key | [fill in] | [fill in] |
| Model ID discoverability | [fill in] | [fill in] |
| Docs clarity | [fill in] | [fill in] |
| Serverless availability | [fill in] | Yes — default |
| OpenAI compatibility | [fill in] | Full |

---

## Summary

- **Overall deployment experience (1–5)**: [fill in]
- **Key friction points**: [summarise top 2–3]
- **What worked well**: [fill in]
- **Time to first token from signup**: [fill in]
