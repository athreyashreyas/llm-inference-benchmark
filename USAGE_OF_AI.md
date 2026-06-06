# Usage of AI (Claude Code)

This document records every significant task delegated to Claude Code throughout this project. Updated after each completed task. The agentic-first approach is a core requirement of this task — this file is evidence of that approach.

---

## Log

| # | Task | What was prompted | Output quality | What I reviewed or changed |
|---|------|------------------|----------------|---------------------------|
| 1 | Read and interpret task spec | Provided `claude_code_instructions.md` and `apm-hiring-task.pdf`; asked agent to read both and start Phase 1 | Excellent — agent identified phase structure and produced correct file ordering | Confirmed phase structure matched spec |
| 2 | Create ASSUMPTIONS.md | Agent scaffolded all 12 assumption entries from the spec, including model rationale, deployment strategy, budget constraints, and competitor selection reasoning | High quality — all required entries present, PM framing applied | Reviewed for completeness against spec checklist |
| 3 | Create AGENTIC_LOG.md | Agent initialised the log with format reference and a session bootstrap entry framed as a product observation | Good — correct format, appropriate first entry | Verified entry includes all 7 required fields |
| 4 | Create USAGE_OF_AI.md | Agent created this file | Meta-recursive — agent is documenting itself | Verified format matches spec |
| 5 | Create .gitignore, .env.example, config/ files | Agent generated all config files with env var references, no hardcoded secrets | High quality — matched spec exactly | Verified .env.example has no real keys |
| 6 | Create data/prompts.json | Agent generated 30 prompts across short/medium/long types covering geography, science, history, coding, math, writing | Good — spot-checked for topic diversity and length-appropriateness | Reviewed all 30 prompts for ambiguity and real-time information requirements |
| 7 | Create benchmark/ modules | Agent implemented runner.py, metrics.py, prompts.py, report.py with full type hints, logging, streaming TTFT, concurrency control, cost guard | High quality — complex async code with proper error handling | Reviewed TTFT timing logic, semaphore usage, cost guard thresholds, retry logic |
| 8 | Create tests/test_runner.py | Agent wrote unit tests with mock responses, zero real API calls | Good — covers TTFT calculation, aggregation math, error handling, dry-run | Verified no real API calls in test suite |
| 9 | Create requirements.txt, Makefile | Agent generated both files with correct dependencies and make targets | High quality | Verified make targets match spec |
| 10 | Create deploy/ notes templates | Agent created structured templates for both platforms | Good | Verified all capture fields are present |
| 11 | Create README.md | Agent wrote full README with model rationale, setup instructions, cost estimates, limitations | High quality — PM-framed, evaluator-ready | Reviewed for completeness and clarity |
| 12 | Create CHANGELOG.md | Agent generated initial changelog entry | Standard | Verified format |

---

## Observations on Using Claude Code for This Task

**What worked well:**
- Scaffolding large file structures from detailed specifications — the agent reliably translated spec requirements into working file content
- Generating coherent Python async code with proper error handling on the first pass
- Maintaining consistent framing (PM persona, product impact language) across documentation files

**Where human judgment was required:**
- Deciding model ID strings to use before platform verification (agent correctly flagged these as TBD)
- Reviewing agentic log entries for genuine product insight vs. surface-level bug reports
- Deciding which friction points merit Severity 3 vs. Severity 2 classification

**What this demonstrates:**
Claude Code can handle the mechanical complexity of a multi-file project build in a single session. The PM value-add is not in the code generation — it is in the product observations, the framing of friction as business impact, and the recommendations that emerge from genuine deployment experience.

---

*This file is updated in real time. Phase 2 and Phase 3 entries will be added as deployment and benchmarking proceed.*
