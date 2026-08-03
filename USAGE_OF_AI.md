# Usage of AI (Claude Code)

Every significant task delegated to Claude Code on this project, logged as it happened. Building the whole thing agent-first was the point, not a shortcut: handing deployment to something that can only read docs and call APIs is a good way to find out which parts of a platform genuinely work from code — most of [AGENTIC_LOG.md](AGENTIC_LOG.md) came out of exactly that.

The session began with one comprehensive brief — [PROJECT_BRIEF.md](PROJECT_BRIEF.md) — handed to Claude Code before any file in this repo existed, along with notes on where reality later diverged from the plan (model fallback chain, GPU choice, deployment type). Worth reading first: the rationale running through `ASSUMPTIONS.md` and `README.md` was specified there before a line of code was written. The timeline below is the record of the agent executing against it, and of where I had to step in.

---

## Log

### Phase 1 — Repository Build

| # | Task | What was prompted | Output quality | What I reviewed or changed |
|---|------|------------------|----------------|---------------------------|
| 1 | Read and interpret the brief | Provided [PROJECT_BRIEF.md](PROJECT_BRIEF.md); asked the agent to read it fully and start Phase 1 | Excellent — agent identified the phase structure and produced correct file ordering | Confirmed the phase structure matched the brief |
| 2 | Create ASSUMPTIONS.md | Agent scaffolded all 12 assumption entries from the brief, including model rationale, deployment strategy, budget constraints, and competitor selection reasoning | High quality — all required entries present, product framing applied | Reviewed for completeness against the brief's checklist |
| 3 | Create AGENTIC_LOG.md | Agent initialised the log with format reference and a session bootstrap entry framed as a product observation | Good — correct format, appropriate first entry | Verified entry includes all 7 required fields |
| 4 | Create USAGE_OF_AI.md | Agent created this file | Meta-recursive — agent is documenting itself | Verified the format matched the brief |
| 5 | Create .gitignore, .env.example, config/ files | Agent generated all config files with env var references, no hardcoded secrets | High quality — matched the brief exactly | Verified .env.example has no real keys |
| 6 | Create data/prompts.json | Agent generated 30 prompts across short/medium/long types covering geography, science, history, coding, math, writing | Good — spot-checked for topic diversity and length-appropriateness | Reviewed all 30 prompts for ambiguity and real-time information requirements |
| 7 | Create benchmark/ modules | Agent implemented runner.py, metrics.py, prompts.py, report.py with full type hints, logging, streaming TTFT, concurrency control, cost guard | High quality — complex async code with proper error handling | Reviewed TTFT timing logic, semaphore usage, cost guard thresholds, retry logic |
| 8 | Create tests/test_runner.py | Agent wrote unit tests with mock responses, zero real API calls | Good — covers TTFT calculation, aggregation math, error handling, dry-run | Verified no real API calls in test suite |
| 9 | Create requirements.txt, Makefile | Agent generated both files with correct dependencies and make targets | High quality | Verified make targets matched the brief |
| 10 | Create deploy/ notes templates | Agent created structured templates for both platforms | Good | Verified all capture fields are present |
| 11 | Create README.md | Agent wrote full README with model rationale, setup instructions, cost estimates, limitations | High quality — led with product framing rather than code | Reviewed for completeness and clarity |
| 12 | Create CHANGELOG.md | Agent generated initial changelog entry | Standard | Verified format |

---

### Phase 2 — Deployment

| # | Task | What was prompted | Output quality | What I reviewed or changed |
|---|------|------------------|----------------|---------------------------|
| 13 | Switch model from Qwen3 4B to Gemma 3 4B Instruct | Prompted after confirming Qwen3 4B was absent from Simplismart marketplace; asked agent to update all configs, scripts, and docs | Good — updated .env.example, platforms.yaml, deploy scripts | Checked for any remaining Qwen3 references via grep |
| 14 | Write deploy/deploy_simplismart.py | Agent wrote the compile-then-deploy flow using the Simplismart SDK, with COST CHECKPOINT, compilation polling, health polling, and env var writing | High quality on first pass — async-safe, idempotent design | Reviewed COST CHECKPOINT prompt, verified scale_to_zero_enabled=True |
| 15 | Debug Simplismart A100 zero quota error | Agent received `"gpu a100: need 1 but only 0.0 available"` and switched ACCELERATOR to `nvidia-h100` | Correct diagnosis and fix — no wasted attempts | Approved the switch to H100 |
| 16 | Debug Simplismart 500 on create_deployment() | Deployment silently created on 500; second attempt got 400 "already exists". Agent diagnosed by calling list_deployments() and found the orphaned deployment | Excellent — agent correctly identified the need for `list_deployments()` as fallback; documented as AGENTIC_LOG entry | Reviewed the recovery approach; manually checked deployment UUID in Simplismart UI |
| 17 | Add `--deploy-only` flag and idempotency to deploy_simplismart.py | Asked agent to avoid re-compilation on each retry; agent added UUID-in-env check, name-based existing-repo check, and `--deploy-only` CLI flag | Good — all three fallback layers correct | Verified Makefile added `deploy-simplismart-only` target |
| 18 | Discover and fix Simplismart `id` header requirement | Inference calls failed silently; agent discovered `id: <uuid>` header requirement from `api_details.curl` in the get_model_deployment() response | Excellent — correct fix: added `extra_headers` to platforms.yaml and updated load_platform_config() to handle nested dicts | Reviewed the platforms.yaml change and runner.py update |
| 19 | Write deploy/deploy_fireworks.py | Agent wrote REST-based deployment using the Fireworks REST API with shape discovery, H100 fallback, COST CHECKPOINT, polling | Good — shape discovery path correctly implemented even though 404 in practice | Reviewed COST CHECKPOINT, verified minReplicaCount=0 and autoscalingPolicy |
| 20 | Debug Fireworks model ID 404 | `gemma-3-4b-instruct` returned 404; agent listed all Gemma models via GET /v1/accounts/fireworks/models?pageSize=200 and found `gemma-3-4b-it` | Excellent — direct API enumeration, correct fix | Confirmed model ID in Fireworks console |
| 21 | Fix Fireworks teardown DELETE 400 | Recent inference requests blocked deletion; agent added `?ignoreChecks=true` query param | Correct and targeted fix | Verified teardown_fireworks.py handles 200 and 204 as success |
| 22 | Run P0 benchmark on both platforms | Prompted `make benchmark-p0`; agent confirmed deployment health first, then ran 45 requests per platform with warm-up | Benchmark completed — 100% success rate, 45 requests each | Reviewed summary CSV to verify scenario IDs and concurrency levels matched experiment matrix |
| 23 | Add AGENTIC_LOG.md Phase 2 entries | Asked agent to document all Phase 2 friction points in log format with product impact and recommended fix | High quality — 5 entries, all with correct severity, evidence, and product framing | Reviewed for accuracy against what actually happened |

---

### Phase 3 — Report and Documentation

| # | Task | What was prompted | Output quality | What I reviewed or changed |
|---|------|------------------|----------------|---------------------------|
| 24 | Generate benchmark report | Agent ran `make report` to produce report/REPORT.md and 6 charts from summary CSV | High quality — narrative analysis identifies the TTFT gap as the defining result with correct quantification | Reviewed all numbers against summary CSV to verify accuracy |
| 25 | Commit and push to GitHub | Asked agent to stage all files (excluding .env) and push to GitHub | Correct — no secrets committed; .gitignore preserved | Reviewed git diff before approving push |
| 26 | Full cohesion and reproducibility audit | Asked agent to read every file and identify inconsistencies | Found 7 issues: Makefile bare python, .env.example stale comment, CHANGELOG stale, USAGE_OF_AI incomplete, deploy notes blank, duplicate AGENTIC_LOG separator, runner.py cost rate discrepancy | Fixed all identified issues |

---

## Observations on Using Claude Code for This Project

**What worked well:**
- Scaffolding large file structures from detailed specifications — the agent reliably translated spec requirements into working file content
- Generating coherent Python async code with proper error handling on the first pass
- Maintaining consistent framing (product-impact language rather than bug-report language) across documentation files
- Debugging API errors by reasoning about what information is available and where to look — e.g., discovering the `id` header requirement from `api_details.curl` in the deployment response, discovering the correct Fireworks model ID by listing all models
- Idempotent script design — the agent recognised the need for compile-once-deploy-many behaviour without being explicitly asked

**Where human judgment was required:**
- Deciding model ID strings to use before platform verification (agent correctly flagged these as TBD)
- Approving cost checkpoints before GPU deployment creation
- Confirming H100 availability on both platforms before switching from A100
- Reviewing agentic log entries for genuine product insight vs. surface-level bug reports
- Deciding which friction points merit Severity 3 vs. Severity 2 classification

**What I took from it:**
Claude Code handled the mechanical complexity of a multi-file build and an API debugging session in one sitting, and it did the platform archaeology — enumerating models, reading deployment response payloads for undocumented headers — faster and more patiently than I would have. What it couldn't do was decide what any of it *meant*. The severity calls, the "we have credits, so why is this failing?" reasoning that led to the Fireworks billing gate, the judgement about which frictions are real product gaps versus my own unfamiliarity — those stayed with me. The agent surfaces evidence; interpreting it is still the job.
