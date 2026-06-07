# Agentic UX Log

This log captures every friction point encountered while attempting to deploy and benchmark Simplismart and Fireworks AI programmatically. Each entry is written in real time, not retrospectively.

**Framing**: Every friction point is analysed as a product experience failure — not just a technical annoyance — with cost to developers building agentic applications and a concrete recommended fix.

**Log started**: 2026-06-06 | Phase 1 (repository build, zero API calls)

---

## Format Reference

```
## [Platform] — [Short descriptive title]

- Stage: signup | api-discovery | deploy | config | api-call | debug | documentation
- What happened: [exactly what was attempted, what occurred]
- Agent impact: Yes / Partially / No (could the agent recover and proceed autonomously?)
- Severity: 1 = cosmetic | 2 = adds time/complexity | 3 = blocks progress
- Evidence: [exact error text, missing doc section, or UI step required]
- Product impact: [cost to a developer building an agentic app]
- Recommended fix: [specific, concrete platform change]
```

---

## Session Bootstrap — Agentic-first approach initiated

- Stage: documentation
- What happened: Before any API call, I attempted to derive all required configuration (base URLs, model IDs, auth endpoints, deployment options) from public documentation at docs.simplismart.ai and docs.fireworks.ai. This was done via the coding agent — no browser interaction at this stage.
- Agent impact: Partially — base URLs and auth mechanism were derivable, but exact model ID strings required UI verification.
- Severity: 2
- Evidence: The instructions note: "Do not hardcode assumed model IDs. Wrong IDs cause silent 404s. Always verify first." This confirms the documentation does not canonically expose model IDs in a machine-readable format.
- Product impact: An agentic deployment workflow cannot be fully scripted without first manually confirming model IDs. This breaks the "zero-human-in-loop" promise of agentic infrastructure tooling.
- Recommended fix: Both platforms should expose a `GET /models` endpoint returning the exact inference-ready model ID strings, matching what must be passed in API calls. Simplismart's marketplace UI should have a "copy model ID" button with exact API string.

---

## Simplismart — Wrong base URL in external spec / no canonical source of truth

- Stage: api-discovery
- What happened: The task spec (and initial `.env.example`) stated `https://api.simplismart.ai/v1` as the base URL. Fetching Simplismart's public docs revealed the correct URL is `https://api.simplismart.live/chat/completions` — a completely different domain (`.live` not `.ai`) with no `/v1` prefix. A `GET /models` endpoint was not found; the correct URL was only discoverable by reading individual model API reference pages.
- Agent impact: No — the agent had the wrong base URL baked in and would have received connection errors on every request without manual correction.
- Severity: 3
- Evidence: `https://docs.simplismart.ai/api-reference/inference/llama3.1-8B` shows `url = "https://api.simplismart.live/chat/completions"`. The domain `api.simplismart.ai` does not appear anywhere in docs.
- Product impact: Any developer starting from the platform's main site, pricing page, or a third-party reference will have the wrong base URL. An agentic workflow will silently fail (connection error or DNS failure) with no helpful error pointing to the correct domain. This is a day-one blocker.
- Recommended fix: (1) Add the correct base URL prominently to the main API reference landing page and the quickstart. (2) Have `api.simplismart.ai` redirect to `api.simplismart.live` with a 301 so stale URLs don't hard-fail. (3) Expose `GET /models` so agents can self-discover the correct endpoint.

---

## Simplismart — Qwen3 4B listed on pricing page but has no API reference doc or model ID

- Stage: api-discovery
- What happened: Qwen3 4B appears on the Simplismart pricing page at $0.10/1M tokens. However, no API reference page exists for it in docs (every other model — Llama, Gemma, DeepSeek — has its own page with an exact model ID string and code example). A search of all doc pages returned no Qwen3 4B entry. The marketplace UI that would reveal the model ID requires authentication, blocking programmatic discovery entirely.
- Agent impact: No — there is no documented model ID string. The agent's best guess (`Qwen/Qwen3-4B-Instruct`, inferred from the HuggingFace naming pattern used by other Simplismart models) is unverified and may cause a silent 404 on the first API call.
- Severity: 3
- Evidence: `llms.txt` index lists Qwen models as "Qwen (14B, 32B)" only. Search across `docs.simplismart.ai` returns no page for Qwen3 4B. Pricing page URL: `simplismart.ai/pricing`.
- Product impact: A model on the pricing page that cannot be called without manually logging into the marketplace to find its ID is not programmatically deployable. This breaks the "deploy in minutes" promise for any developer starting from docs rather than the UI.
- Recommended fix: Every model on the pricing page must have a corresponding API reference doc page with the exact model ID string, a copy button, and a working code example. The model ID should also be returned by a `GET /models` endpoint so agents can enumerate available models without touching a browser.

---

## Simplismart — Qwen3 4B on pricing page but absent from marketplace — and the fallback chain it triggered

- Stage: deploy
- What happened: After logging into Simplismart marketplace, Qwen3 4B was not available for deployment despite being listed on the public pricing page at $0.10/1M tokens. The smallest available Qwen3 variant in the marketplace was Qwen3 14B, so the benchmark model was provisionally switched to Qwen3 14B to keep momentum. That choice didn't survive contact with the second platform: attempting to provision Qwen3-14B on Fireworks AI with `NVIDIA_H100_80GB` returned a 404 — Fireworks only exposes `NVIDIA_H200_141GB` for that model (see "Fireworks AI — H100 returns 404 for some models but not others" below). Re-running the same model/GPU discovery gauntlet on a *second* platform, for a model that was itself already a fallback, is what prompted reconsidering the model choice entirely. The model that was finally settled on — Gemma 3 4B Instruct — is the only one confirmed deployable with H100 on **both** platforms (Simplismart: 200 on compile/deploy; Fireworks: 200 on `accounts/fireworks/models/gemma-3-4b-it` + `NVIDIA_H100_80GB`, vs. the 404 for `qwen3-14b`). That cross-platform H100 compatibility — not raw model preference — is what decided the final pick.
- Agent impact: No — the agent had a confirmed model selection (Qwen3 4B) that turned out to be undeployable, then a second confirmed selection (Qwen3 14B) that turned out to be GPU-incompatible on the competitor platform. Both pivots required human UI exploration / cross-platform API probing to resolve. Gemma 3 4B Instruct is the model used throughout this benchmark — README, ASSUMPTIONS.md, CHANGELOG.md, and report/REPORT.md are all consistent on it.
- Severity: 3
- Evidence: Simplismart pricing page lists "Qwen3 4B — $0.10/1M tokens"; marketplace login revealed Qwen3 14B as the smallest available Qwen3 deployment option (no Qwen3 4B endpoint found); Fireworks `POST /deployments` for `qwen3-14b` + `NVIDIA_H100_80GB` → 404 ("only NVIDIA_H200_141GB available for this model" per UI); Fireworks `POST /deployments` for `gemma-3-4b-it` + `NVIDIA_H100_80GB` → 200.
- Product impact: Two independent discoverability gaps compounded into a full model-selection pivot mid-task. (1) Simplismart's pricing page and marketplace inventory are out of sync — a developer who picks a model from pricing and wires it into their code hits a silent deployment failure. (2) Fireworks' GPU-to-model compatibility is opaque and platform-specific — there's no API to ask "which accelerators does this model support" before attempting a deployment. Together, a developer trying to run the *same* model on the *same* GPU class across two platforms — exactly what a fair benchmark requires — has no reliable way to find a combination that both platforms actually support without trial-and-error deploy attempts.
- Recommended fix: (1) Simplismart's pricing page should only list models with active, deployable endpoints, with a real-time availability indicator ("Available now" / "Coming soon"). (2) Both platforms should expose a `supportedAcceleratorTypes`-style field on model metadata so a developer (or an agent) can intersect "models on platform A" × "models on platform B" × "valid GPUs for that model on each platform" with a single API call, instead of discovering incompatibilities one failed deployment at a time.

---

## Fireworks AI — API key creation requires existing credentials (bootstrap problem)

- Stage: api-discovery
- What happened: Fireworks has a documented `POST /v1/accounts/{id}/users/{id}/apiKeys` endpoint for programmatic key creation. However, this endpoint requires Bearer authentication with an existing API key. There is no unauthenticated path to generate a first key — the initial key must be created via the Dashboard UI.
- Agent impact: Partially — after the first manual key creation, all subsequent key management (rotation, provisioning for sub-users) could be scripted. Only the bootstrap is blocked.
- Severity: 2
- Evidence: Fireworks API key creation docs state "Bearer authentication using your Fireworks API key" is required. See `docs.fireworks.ai/api-reference/create-api-key.md`.
- Product impact: For a developer building a multi-tenant app that needs to provision API keys per customer, the workflow cannot be fully automated from zero. The first key for any new account always requires a human with browser access.
- Recommended fix: This is a known hard problem (the key-to-get-a-key bootstrap). Mitigations: (1) Service account tokens creatable via OAuth that can then generate API keys; (2) A CLI login flow (`firectl login`) that exchanges OAuth credentials for a session token usable for key creation. Fireworks actually has `firectl` — worth documenting this path more prominently as the agentic bootstrap solution.

---

## Simplismart — Two different base URLs for two different API surfaces, not explained anywhere

- Stage: documentation
- What happened: Attempting to find the correct inference base URL surfaced two completely different domains: `https://api.app.simplismart.ai` (referenced in the Python SDK docs for deployment management — model compilation, health checks, deployment creation) and `https://api.simplismart.live` (referenced in model-specific API reference pages for inference/chat completions). Neither doc page explains that these are separate API surfaces or when to use which. A developer reading the SDK quickstart would configure the wrong URL for inference and get no useful error.
- Agent impact: No — the agent would have used whichever URL it found first. Finding both required reading multiple disconnected doc sections with no cross-references.
- Severity: 3
- Evidence: `docs.simplismart.ai/sdk/python/overview` sets `SIMPLISMART_BASE_URL=https://api.app.simplismart.ai`. `docs.simplismart.ai/api-reference/inference/llama3.1-8B` uses `https://api.simplismart.live/chat/completions`. Neither page mentions the other.
- Product impact: A developer building an agentic pipeline that does both deployment management and inference — a completely normal use case — has to discover by trial and error that these are two separate API surfaces on two separate domains. This is a significant integration tax. It also means there is no single SDK client that covers both surfaces.
- Recommended fix: Create an API overview page that explicitly maps each base URL to its purpose, with a table: "Management API (deployment, compilation): `api.app.simplismart.ai`; Inference API (chat completions): `api.simplismart.live`." Add cross-links between the SDK docs and the inference API reference. Ideally, consolidate under one domain long-term.

---

## Simplismart — Auth credential has two different names across docs

- Stage: documentation
- What happened: The Python SDK docs call the auth credential `SIMPLISMART_PG_TOKEN` ("Playground Token"), while the inference API reference pages show it as a Bearer token obtained from "Settings → API Keys" with no name. A developer reading only the SDK docs would look for a "PG Token" field in Settings; a developer reading only the inference docs would look for an "API Key." Both point to the same credential.
- Agent impact: Partially — an agent scanning docs for "API key" would not find the `SIMPLISMART_PG_TOKEN` environment variable name and vice versa. Config scaffolding from one doc surface would be incompatible with the other.
- Severity: 2
- Evidence: `docs.simplismart.ai/sdk/python/overview`: `export SIMPLISMART_PG_TOKEN="your_pg_token_here"`. Inference API pages: `"Authorization": "Bearer YOUR_JWT_TOKEN"`. Settings page likely labels it as "API Key."
- Product impact: Credential naming confusion is a common cause of failed integrations. When the same secret has three names across three surfaces (PG Token, JWT Token, API Key), support ticket volume increases and developer confidence in the platform decreases.
- Recommended fix: Standardise on one name across all documentation, UI labels, and SDK variable names. "API Key" is the industry-standard term. Update SDK docs to use `SIMPLISMART_API_KEY` and remove the "PG Token" terminology, or at minimum add a note: "This is the same credential shown as 'API Key' in Settings."

---

## Fireworks AI — GPU availability for a model not discoverable without UI access

- Stage: deploy
- What happened: Attempted to deploy Qwen3-14B with `NVIDIA_H100_80GB` via the REST API (and SDK). The SDK's `accelerator_type` enum lists H100 as a valid value. However, the Fireworks UI shows only `NVIDIA_H200_141GB` as available for this specific model — H100 is not offered. The API would have rejected the H100 request at the backend level despite it being a valid enum value in the SDK.
- Agent impact: No — an agent following the SDK enum alone would have submitted an invalid GPU type for this model and received an opaque error with no self-correction path. The correct GPU had to be discovered via UI inspection.
- Severity: 3
- Evidence: Fireworks SDK `accelerator_type` enum includes `NVIDIA_H100_80GB`. Fireworks UI deployment page for `accounts/fireworks/models/qwen3-14b` shows only `NVIDIA_H200_141GB` as selectable. `deployment_shapes.list()` returns 403 — programmatic GPU discovery is not available without elevated permissions.
- Product impact: An agentic deployment workflow cannot programmatically determine which GPUs are valid for a given model. The agent must either guess from the SDK enum (likely wrong) or require a human UI check. This breaks the "deploy in minutes from code" promise entirely for dedicated GPU endpoints.
- Recommended fix: (1) Expose a `GET /models/{id}/deployment-shapes` endpoint returning valid GPU options per model — no elevated permissions required. (2) Return a descriptive error when an incompatible GPU is specified: "NVIDIA_H100_80GB is not available for this model. Available: NVIDIA_H200_141GB." rather than a generic 400. (3) Add GPU availability to model metadata in the models list endpoint.

---

## Simplismart — Deployment API returns 500 but silently creates the deployment

- Stage: deploy
- What happened: `client.create_deployment()` returned `SimplismartError (status=500)`. The script treated this as a failure and exited. On retry, the API returned 400: "Deployment with this name already exists in this workspace." — meaning the 500 response was a server-side serialization failure on a deployment that had actually been created successfully. The deployment ID was unrecoverable from the error response.
- Agent impact: No — the deployment was live and healthy but the agent had no ID for it. Recovery required a separate `list_deployments()` call to discover the orphaned deployment.
- Severity: 3
- Evidence: First attempt: `SimplismartError: Simplismart API error (status=500)`. Second attempt: `SimplismartError: Simplismart API error (status=400) payload={'non_field_errors': ['Deployment with this name already exists in this workspace.']}`. `list_deployments()` returned `status=DEPLOYED` with the correct UUID.
- Product impact: An agentic deployment workflow that trusts HTTP status codes will treat a 500 as a hard failure and either retry (creating a duplicate) or abort (losing the deployment ID). There is no safe recovery path from the SDK alone — the agent must know to call `list_deployments()` as a fallback, which is not documented anywhere.
- Recommended fix: (1) Fix the server-side 500 so the response always includes the created resource on success. (2) Make the deployment creation idempotent: a second `POST` with the same name should return the existing deployment with a 200 or 409+resource, not a 400. (3) Document the `list_deployments()` recovery pattern explicitly.

---

## Simplismart — Dedicated deployments require a non-standard `id` header on every inference request

- Stage: api-call
- What happened: After deployment, inference calls using the standard OpenAI client (with just `Authorization` and `Content-Type` headers) returned errors. The correct request requires an additional `id: <deployment_uuid>` header on every call. This was discoverable only by inspecting the `api_details.curl` field in the `get_model_deployment()` response — it is not mentioned in the SDK quickstart, the deployment docs, or the inference API reference.
- Agent impact: No — the agent had no way to know this header was required. The inference endpoint looks like a standard OpenAI-compatible URL, which implies standard headers. Only reading the full deployment detail JSON revealed the requirement.
- Severity: 3
- Evidence: `api_details.curl` in deployment response includes `-H "id: 7e734fe1-bb87-4bf8-9cd2-dcfd2e024420"`. The Python SDK example also shows `default_headers={"id": "<deployment_uuid>"}`. Neither the quickstart nor the deployment guide mentions this.
- Product impact: Any developer who reads the quickstart, deploys a model, and tries to call it with a standard OpenAI client will get authentication or routing errors with no useful message pointing to the missing header. The custom header breaks drop-in OpenAI SDK compatibility.
- Recommended fix: (1) Document the required `id` header prominently in the deployment guide and quickstart, immediately after the deployment creation step. (2) Return the complete inference code snippet (including the `id` header) from `create_deployment()` in the SDK response, not just from `get_model_deployment()`. (3) Ideally, route by subdomain or path rather than requiring a custom header — the current proxy URL `http.{slug}-proxy.ss-in.s9t.link` already uniquely identifies the deployment and could serve as the sole routing mechanism.

---

## Simplismart — A100 GPU has zero quota despite being listed as a valid accelerator

- Stage: deploy
- What happened: Attempted compilation with `accelerator_type="nvidia-a100"`. The API returned HTTP 400: `"gpu a100: need 1 but only 0.0 available. For additional quota, please reach out to support@simplismart.ai"`. The SDK's accelerator enum and the deployment UI both list A100 as a valid type. H100 succeeded without issue.
- Agent impact: No — the SDK enum implies availability but the actual quota is 0. No programmatic way to check GPU quota before attempting.
- Severity: 2
- Evidence: `SimplismartError: gpu a100: need 1 but only 0.0 available (status=400)`.
- Product impact: A developer choosing A100 (e.g. for cost reasons) will get a cryptic quota error with no self-serve resolution path. The only fix is to email support.
- Recommended fix: Expose a `GET /gpus/availability` endpoint returning current quotas per GPU type. Show real-time availability in the marketplace deployment UI next to each GPU option. Reserve enum values for GPUs the account can actually use.

---

## Fireworks AI — `deploymentShapeVersions` endpoint returns 404 for all accounts

- Stage: deploy
- What happened: The Fireworks API docs describe a `GET /v1/accounts/{id}/deploymentShapeVersions` endpoint for discovering available deployment shapes. Calling this endpoint for both the `fireworks` account (public shapes) and the user's own account returns HTTP 404 "Not Found". The deployment shape approach documented in the official API spec is therefore unusable without out-of-band knowledge of shape names.
- Agent impact: No — shape discovery failed silently. The fallback to direct `acceleratorType` worked, but only because H100 happened to be available for this model.
- Severity: 2
- Evidence: `GET /v1/accounts/fireworks/deploymentShapeVersions → 404`. `GET /v1/accounts/athreya-shreyas-np8t/deploymentShapeVersions → 404`.
- Product impact: The recommended deployment path (use a shape) is inaccessible. Developers must guess or hardcode shape names, or fall back to the accelerator-type approach and hope the GPU is available for their model.
- Recommended fix: Make `deploymentShapeVersions` publicly accessible (no elevated permissions required) and return shapes filtered by the requesting account's eligible models. Alternatively, expose shape availability via the model detail endpoint: `GET /v1/accounts/fireworks/models/{id}` should include `availableDeploymentShapes`.

---

## Fireworks AI — H100 returns 404 for some models but not others; no programmatic way to know

- Stage: deploy
- What happened: `NVIDIA_H100_80GB` with `accounts/fireworks/models/qwen3-14b` returned 404 "resource not found" via both `POST /deployments` and `validateOnly=true`. The same GPU type with `accounts/fireworks/models/gemma-3-4b-it` returned 200. The Fireworks UI reportedly shows H200 as the only option for qwen3-14b. There is no API endpoint to check GPU availability per model before attempting deployment.
- Agent impact: No — the agent cannot determine upfront which GPU types are valid for a given model. The only signal is a 404 on deployment creation, which is indistinguishable from other 404 causes.
- Severity: 3
- Evidence: `POST /deployments {baseModel: qwen3-14b, acceleratorType: NVIDIA_H100_80GB} → 404`. `POST /deployments {baseModel: gemma-3-4b-it, acceleratorType: NVIDIA_H100_80GB} → 200`.
- Product impact: An agentic workflow cannot reliably plan GPU selection without trial-and-error. A model switch (e.g. from qwen3-14b to gemma-3-4b-it) silently changes which GPUs are valid — this breaks any scripted deployment that parameterises model and GPU independently.
- Recommended fix: Return a descriptive error: "NVIDIA_H100_80GB is not available for accounts/fireworks/models/qwen3-14b. Available options: NVIDIA_H200_141GB." Add `supportedAcceleratorTypes` to the model detail response so agents can pre-check before calling `POST /deployments`.

