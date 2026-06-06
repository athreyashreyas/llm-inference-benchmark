# Simplismart Deployment Notes

*Template populated during Phase 1. Real observations added during Phase 2.*

---

## Signup and API Key

- **Signup URL**: app.simplismart.ai
- **Account creation method**: [ ] Email / [ ] Google / [ ] GitHub
- **API key location**: Settings > API Keys
- **Time to obtain API key from signup**: [fill in during Phase 2]
- **Was key generation programmable via API?**: [ ] Yes / [ ] No (document in AGENTIC_LOG.md if No)
- **Scoping options on API key**: [describe — e.g., read-only, full-access, per-model]

---

## Model Verification

- **Model searched for**: Gemma 3 4B Instruct (`google/gemma-3-4b-it`)
- **Exact model ID found in marketplace**: `google/gemma-3-4b-it` (HuggingFace ID used for compilation); inference model name is `gemma-it`
- **Location of model ID**: [e.g., Marketplace > Model card > "API ID" field]
- **Was model ID available in a `GET /models` API call?**: [ ] Yes / [ ] No
- **Any ambiguity in model ID format**: [describe — e.g., multiple variants listed]
- **Cross-reference**: AGENTIC_LOG.md entry #[N]

---

## Deployment Type

- **Deployment used**: [ ] Shared/serverless (marketplace) / [ ] Dedicated endpoint
- **If dedicated**: GPU type selected: [ ], Autoscale configured: min=[ ] max=[ ]
- **If autoscale unavailable**: Manual pause performed: [ ] Yes / [ ] No
- **Endpoint URL confirmed**: [fill in]

---

## First Successful API Call

```bash
# curl test command used:
# curl https://api.simplismart.ai/v1/chat/completions \
#   -H "Authorization: Bearer $SIMPLISMART_API_KEY" \
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
- [ ] Deployment configuration not automatable — LOG ENTRY #[ ]
- [ ] Streaming response format differed from OpenAI spec — LOG ENTRY #[ ]
- [ ] Rate limit headers absent or non-standard — LOG ENTRY #[ ]
- [ ] Other: [describe]

---

## Screenshots to Capture

*(Actual images to be added to `report/screenshots/` manually)*

- [ ] Marketplace page showing Gemma 3 4B model listing (`google/gemma-3-4b-it`)
- [ ] Model detail page showing exact API model ID
- [ ] API key settings page
- [ ] Deployment configuration page (if dedicated)
- [ ] First successful API response in terminal

---

## Summary

- **Overall deployment experience (1–5)**: [fill in]
- **Key friction points**: [summarise top 2–3]
- **What worked well**: [fill in]
- **Time to first token from signup**: [fill in]
