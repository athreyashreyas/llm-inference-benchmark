"""Async benchmark runner for LLM inference across Simplismart and Fireworks AI."""

from __future__ import annotations

import asyncio
import logging
import os
import random
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from dotenv import load_dotenv
from openai import AsyncOpenAI

from benchmark.metrics import compute_summary, save_raw_csv, save_summary_csv
from benchmark.prompts import load_prompts, shuffle_prompts

load_dotenv()

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------

LOG_DIR = Path(__file__).parent.parent / "data" / "results"
LOG_DIR.mkdir(parents=True, exist_ok=True)

_log_file = LOG_DIR / f"run_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(_log_file),
    ],
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Config loading
# ---------------------------------------------------------------------------

CONFIG_DIR = Path(__file__).parent.parent / "config"


def _load_yaml(path: Path) -> Dict:
    with open(path) as f:
        return yaml.safe_load(f)


def _expand_env(value: str) -> str:
    """Expand ${VAR} placeholders from environment variables."""
    import re
    return re.sub(r"\$\{(\w+)\}", lambda m: os.environ.get(m.group(1), ""), value)


def load_platform_config(name: str) -> Dict:
    """Load and env-expand config for a named platform. Handles nested dicts."""
    raw = _load_yaml(CONFIG_DIR / "platforms.yaml")[name]
    result = {}
    for k, v in raw.items():
        if isinstance(v, dict):
            result[k] = {ik: _expand_env(str(iv)) for ik, iv in v.items()}
        else:
            result[k] = _expand_env(str(v))
    return result


def load_benchmark_config() -> Dict:
    return _load_yaml(CONFIG_DIR / "benchmark.yaml")


# ---------------------------------------------------------------------------
# Experiment matrix
# ---------------------------------------------------------------------------

SCENARIOS = [
    {"id": "E01", "platform": "simplismart", "prompt_type": "short",  "max_tokens": 50,  "concurrency": 1,  "reps": 15, "priority": "p0"},
    {"id": "E02", "platform": "simplismart", "prompt_type": "medium", "max_tokens": 150, "concurrency": 1,  "reps": 15, "priority": "p0"},
    {"id": "E03", "platform": "simplismart", "prompt_type": "short",  "max_tokens": 50,  "concurrency": 5,  "reps": 15, "priority": "p0"},
    {"id": "E04", "platform": "simplismart", "prompt_type": "medium", "max_tokens": 150, "concurrency": 5,  "reps": 10, "priority": "p1"},
    {"id": "E05", "platform": "simplismart", "prompt_type": "long",   "max_tokens": 200, "concurrency": 10, "reps": 10, "priority": "p1"},
    {"id": "E06", "platform": "fireworks",   "prompt_type": "short",  "max_tokens": 50,  "concurrency": 1,  "reps": 15, "priority": "p0"},
    {"id": "E07", "platform": "fireworks",   "prompt_type": "medium", "max_tokens": 150, "concurrency": 1,  "reps": 15, "priority": "p0"},
    {"id": "E08", "platform": "fireworks",   "prompt_type": "short",  "max_tokens": 50,  "concurrency": 5,  "reps": 15, "priority": "p0"},
    {"id": "E09", "platform": "fireworks",   "prompt_type": "medium", "max_tokens": 150, "concurrency": 5,  "reps": 10, "priority": "p1"},
    {"id": "E10", "platform": "fireworks",   "prompt_type": "long",   "max_tokens": 200, "concurrency": 10, "reps": 10, "priority": "p1"},
]

# Cost per million tokens used for the in-flight cost guard only (not for CSV reporting).
# Intentionally conservative: blended input+output rate, Fireworks higher to account for
# uncertainty on dedicated GPU token pricing. Reporting uses metrics.py COST_PER_M_OUTPUT_TOKENS.
COST_PER_M_TOKENS = {
    "simplismart": 0.10,
    "fireworks": 0.20,
}

# ---------------------------------------------------------------------------
# Core request function
# ---------------------------------------------------------------------------


async def single_request(
    client: AsyncOpenAI,
    model: str,
    prompt_text: str,
    max_tokens: int,
    bench_cfg: Dict,
    timeout_s: float,
) -> Dict[str, Any]:
    """Make a single streaming chat completion and return timing + token metrics.

    Metrics captured:
      TTFT  — time from request start to first token
      TPOT  — (e2e - TTFT) / (output_tokens - 1): avg time per output token after first
      ITL   — mean of actual inter-token gaps measured from streaming timestamps
      TPS   — output_tokens / e2e_seconds
    """
    result: Dict[str, Any] = {
        "ttft_ms": None,
        "tpot_ms": None,
        "itl_ms": None,
        "e2e_ms": None,
        "input_tokens": None,
        "output_tokens": None,
        "tokens_per_sec": None,
        "status": "error",
        "error_type": None,
    }

    gen_cfg = bench_cfg["generation"]
    retry_cfg = bench_cfg["retry"]

    for attempt in range(retry_cfg["max_attempts_on_5xx"] + 1):
        try:
            t_start = time.perf_counter()
            first_token_time: Optional[float] = None
            token_times: List[float] = []   # arrival time of each content-bearing chunk
            output_chunks = 0
            usage_input = None
            usage_output = None

            async with asyncio.timeout(timeout_s):
                stream = await client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": prompt_text}],
                    max_tokens=max_tokens,
                    temperature=gen_cfg["temperature"],
                    top_p=gen_cfg["top_p"],
                    stream=True,
                )

                async for chunk in stream:
                    now = time.perf_counter()
                    if first_token_time is None:
                        first_token_time = now
                    if chunk.choices and chunk.choices[0].delta.content:
                        token_times.append(now)
                        output_chunks += 1
                    if hasattr(chunk, "usage") and chunk.usage:
                        usage_input = chunk.usage.prompt_tokens
                        usage_output = chunk.usage.completion_tokens

            t_end = time.perf_counter()
            e2e_ms = (t_end - t_start) * 1000
            ttft_ms = ((first_token_time - t_start) * 1000) if first_token_time else None

            # Token counts: use usage field; approximate if missing
            out_tokens = usage_output if usage_output is not None else output_chunks
            in_tokens = usage_input if usage_input is not None else len(prompt_text.split())

            tps = (out_tokens / (e2e_ms / 1000)) if e2e_ms > 0 and out_tokens else None

            # TPOT: derived from total timing — avg ms per output token after first
            tpot_ms: Optional[float] = None
            if ttft_ms is not None and out_tokens and out_tokens > 1:
                tpot_ms = round((e2e_ms - ttft_ms) / (out_tokens - 1), 2)

            # ITL: mean of actual inter-token gaps from streaming timestamps
            itl_ms: Optional[float] = None
            if len(token_times) > 1:
                gaps = [(token_times[i + 1] - token_times[i]) * 1000
                        for i in range(len(token_times) - 1)]
                itl_ms = round(sum(gaps) / len(gaps), 2)

            result.update({
                "ttft_ms": round(ttft_ms, 2) if ttft_ms is not None else None,
                "tpot_ms": tpot_ms,
                "itl_ms": itl_ms,
                "e2e_ms": round(e2e_ms, 2),
                "input_tokens": in_tokens,
                "output_tokens": out_tokens,
                "tokens_per_sec": round(tps, 2) if tps else None,
                "status": "success",
                "error_type": None,
            })
            return result

        except asyncio.TimeoutError:
            result["error_type"] = "TimeoutError"
            logger.warning("Request timed out (attempt %d)", attempt + 1)
            if attempt < retry_cfg["max_attempts_on_5xx"]:
                continue
            return result

        except Exception as exc:
            exc_name = type(exc).__name__
            result["error_type"] = exc_name

            # 429 rate limit: exponential backoff
            if "429" in str(exc) or "rate" in str(exc).lower():
                for backoff_attempt in range(retry_cfg["max_attempts_on_429"]):
                    wait = (
                        retry_cfg["backoff_base_seconds"] * (2 ** backoff_attempt)
                        + random.uniform(0, 0.5)
                    )
                    logger.warning("Rate limited. Backing off %.1fs (attempt %d)", wait, backoff_attempt + 1)
                    await asyncio.sleep(wait)
                    # retry via outer loop by breaking to next attempt
                return result

            # 4xx (not 429): no retry
            if any(code in str(exc) for code in ["400", "401", "403", "404"]):
                logger.error("Non-retryable error: %s", exc)
                return result

            # 5xx: retry
            logger.warning("Server error %s (attempt %d)", exc_name, attempt + 1)
            if attempt < retry_cfg["max_attempts_on_5xx"]:
                continue
            return result

    return result


# ---------------------------------------------------------------------------
# Scenario runner
# ---------------------------------------------------------------------------


async def run_scenario(
    scenario: Dict,
    client: AsyncOpenAI,
    model: str,
    all_prompts: List[Dict],
    bench_cfg: Dict,
    run_id: str,
    is_first_platform: bool,
) -> List[Dict[str, Any]]:
    """Run a single scenario and return raw result rows."""
    prompt_type = scenario["prompt_type"]
    concurrency = scenario["concurrency"]
    reps = scenario["reps"]
    max_tokens = scenario["max_tokens"]
    scenario_id = scenario["id"]
    platform = scenario["platform"]

    type_prompts = [p for p in all_prompts if p["type"] == prompt_type]
    shuffled = shuffle_prompts(type_prompts)

    sem = asyncio.Semaphore(concurrency)
    warmup_count = bench_cfg["warmup"]["requests"]
    timeout_first = bench_cfg["timeouts"]["first_request_seconds"]
    timeout_sub = bench_cfg["timeouts"]["subsequent_seconds"]

    async def bounded_request(prompt: Dict, idx: int) -> Dict[str, Any]:
        async with sem:
            timeout = timeout_first if (is_first_platform and idx == 0) else timeout_sub
            return await single_request(client, model, prompt["text"], max_tokens, bench_cfg, timeout)

    # Warm-up (discarded)
    logger.info("[%s] Warming up with %d requests...", scenario_id, warmup_count)
    warmup_prompts = [random.choice(type_prompts) for _ in range(warmup_count)]
    await asyncio.gather(*[bounded_request(p, i) for i, p in enumerate(warmup_prompts)])

    # Measured run — wall-clock duration covers full concurrent batch
    logger.info("[%s] Running %d reps at concurrency=%d...", scenario_id, reps, concurrency)
    selected_prompts = [shuffled[i % len(shuffled)] for i in range(reps)]
    tasks = [bounded_request(p, i + 1) for i, p in enumerate(selected_prompts)]
    t_bench_start = time.perf_counter()
    raw_results = await asyncio.gather(*tasks)
    benchmark_duration_s = time.perf_counter() - t_bench_start

    timestamp = datetime.now(timezone.utc).isoformat()
    rows = []
    for i, (prompt, result) in enumerate(zip(selected_prompts, raw_results)):
        rows.append({
            "run_id": run_id,
            "platform": platform,
            "scenario_id": scenario_id,
            "concurrency": concurrency,
            "prompt_id": prompt["id"],
            "benchmark_duration_s": round(benchmark_duration_s, 3),
            **result,
            "timestamp": timestamp,
        })

    return rows


# ---------------------------------------------------------------------------
# Cost estimation
# ---------------------------------------------------------------------------


def estimate_cost(results: List[Dict[str, Any]], platform: str) -> float:
    """Estimate total API cost in USD from raw results."""
    total_tokens = sum(
        (r.get("input_tokens") or 0) + (r.get("output_tokens") or 0)
        for r in results
        if r.get("status") == "success"
    )
    rate = COST_PER_M_TOKENS.get(platform, 0.20)
    return (total_tokens / 1_000_000) * rate


# ---------------------------------------------------------------------------
# Platform runner
# ---------------------------------------------------------------------------


async def run_platform(
    platform_name: str,
    scenarios: List[Dict],
    bench_cfg: Dict,
    run_id: str,
    dry_run: bool = False,
    is_first: bool = True,
) -> List[Dict[str, Any]]:
    """Run all scenarios for one platform and return raw results."""
    plat_cfg = load_platform_config(platform_name)
    api_key = plat_cfg.get("api_key", "")
    base_url = plat_cfg.get("base_url", "")
    model = plat_cfg.get("model", "")

    if not api_key or not base_url or not model:
        logger.error("[%s] Missing config (api_key=%s, base_url=%s, model=%s)",
                     platform_name, bool(api_key), bool(base_url), bool(model))
        raise ValueError(f"Incomplete config for platform '{platform_name}'. Check .env file.")

    if dry_run:
        logger.info("[DRY RUN] Would run %d scenarios on %s with model %s", len(scenarios), platform_name, model)
        return []

    extra_headers = plat_cfg.get("extra_headers", {})
    client = AsyncOpenAI(api_key=api_key, base_url=base_url, default_headers=extra_headers)
    all_prompts = load_prompts()
    all_results: List[Dict[str, Any]] = []
    cumulative_cost = 0.0
    cost_warn_threshold = bench_cfg["cost_guard"]["warn_at_usd"]
    cost_abort_threshold = bench_cfg["cost_guard"]["abort_at_usd"]

    # ------------------------------------------------------------------ #
    # Cold start probe — single request before any scenarios.
    # If the deployment has been idle (scale-to-zero), this request triggers
    # GPU spin-up and its TTFT will be anomalously high. Reported separately
    # so it does not inflate the benchmark percentiles.
    # ------------------------------------------------------------------ #
    logger.info("[%s] Cold start probe — measuring first-request TTFT (may include GPU spin-up)...", platform_name)
    cold_probe = await single_request(
        client, model, "Say hello.", max_tokens=5,
        bench_cfg=bench_cfg, timeout_s=120.0,
    )
    cold_start_ttft_ms = cold_probe.get("ttft_ms")
    logger.info("[%s] Cold start TTFT: %s ms", platform_name, cold_start_ttft_ms)

    for scenario in scenarios:
        results = await run_scenario(
            scenario, client, model, all_prompts, bench_cfg, run_id, is_first
        )
        all_results.extend(results)
        is_first = False

        cumulative_cost += estimate_cost(results, platform_name)
        if cumulative_cost >= cost_abort_threshold:
            logger.error("COST ABORT: Estimated spend $%.4f exceeds abort threshold $%.2f on %s",
                         cumulative_cost, cost_abort_threshold, platform_name)
            break
        if cumulative_cost >= cost_warn_threshold:
            logger.warning("COST WARNING: Estimated spend on %s has reached $%.4f", platform_name, cumulative_cost)

    budget_remaining = 5.00 - cumulative_cost
    print(f"\nPlatform {platform_name} complete. {len(all_results)} requests. "
          f"Estimated cost: ${cumulative_cost:.4f}. Budget remaining: ~${budget_remaining:.2f}.")
    print("REMINDER: If using a dedicated deployment, pause or delete it now to stop GPU billing.")

    # Attach cold start metadata to all results so compute_summary can read it
    for r in all_results:
        r["cold_start_ttft_ms"] = cold_start_ttft_ms

    return all_results


# ---------------------------------------------------------------------------
# Main entrypoint
# ---------------------------------------------------------------------------


def validate_env(platforms: List[str]) -> bool:
    """Validate that required env vars are set. Return True if valid."""
    required = {
        "simplismart": ["SIMPLISMART_API_KEY", "SIMPLISMART_BASE_URL", "SIMPLISMART_MODEL_ID"],
        "fireworks": ["FIREWORKS_API_KEY", "FIREWORKS_MODEL_ID"],
    }
    valid = True
    for platform in platforms:
        for var in required.get(platform, []):
            val = os.environ.get(var, "")
            if not val or val in ("your_key_here", ""):
                logger.warning("Missing or placeholder env var: %s", var)
                valid = False
    return valid


async def main(
    platform_filter: str = "both",
    priority_filter: str = "p0",
    scenario_override: Optional[str] = None,
    dry_run: bool = False,
) -> None:
    """Entry point: validate, run scenarios, save results."""
    bench_cfg = load_benchmark_config()
    run_id = str(uuid.uuid4())[:8]

    # Resolve which platforms
    if platform_filter == "both":
        platforms = ["simplismart", "fireworks"]
    else:
        platforms = [platform_filter]

    # Resolve which scenarios
    if scenario_override:
        ids = [s.strip().upper() for s in scenario_override.split(",")]
        scenarios = [s for s in SCENARIOS if s["id"] in ids]
    elif priority_filter == "p0":
        scenarios = [s for s in SCENARIOS if s["priority"] == "p0"]
    else:
        scenarios = SCENARIOS

    # Filter by platform
    platform_scenarios = {
        p: [s for s in scenarios if s["platform"] == p]
        for p in platforms
    }

    if dry_run:
        print("\n=== DRY RUN MODE — No API calls will be made ===")
        valid = validate_env(platforms)
        for p, scens in platform_scenarios.items():
            plat_cfg = load_platform_config(p)
            model = plat_cfg.get("model", "<not set>")
            base_url = plat_cfg.get("base_url", "<not set>")
            extra_headers = plat_cfg.get("extra_headers", {})
            print(f"\nPlatform: {p}")
            print(f"  Base URL: {base_url}")
            print(f"  Model: {model}")
            if extra_headers:
                print(f"  Extra headers: {list(extra_headers.keys())}")
            print(f"  Scenarios: {[s['id'] for s in scens]}")
            total_reps = sum(s["reps"] for s in scens)
            print(f"  Total requests (excl. warmup): {total_reps}")
        print(f"\nEnv vars valid: {valid}")
        print("=== DRY RUN COMPLETE ===\n")
        return

    validate_env(platforms)
    results_dir = LOG_DIR
    all_summaries: List[Dict] = []

    for i, platform in enumerate(platforms):
        scens = platform_scenarios[platform]
        if not scens:
            logger.info("No scenarios for platform %s, skipping.", platform)
            continue

        raw_results = await run_platform(
            platform_name=platform,
            scenarios=scens,
            bench_cfg=bench_cfg,
            run_id=run_id,
            dry_run=False,
            is_first=(i == 0),
        )

        raw_path = results_dir / f"{platform}_{run_id}_raw.csv"
        save_raw_csv(raw_results, raw_path)

        # Build per-scenario summaries
        for scen in scens:
            scen_results = [r for r in raw_results if r["scenario_id"] == scen["id"]]
            if not scen_results:
                continue
            cold_start = scen_results[0].get("cold_start_ttft_ms") if scen_results else None
            summary = compute_summary(scen_results, platform=platform, cold_start_ttft_ms=cold_start)
            all_summaries.append({
                "platform": platform,
                "scenario_id": scen["id"],
                "concurrency": scen["concurrency"],
                **summary,
            })

    if all_summaries:
        summary_path = results_dir / f"summary_{run_id}.csv"
        save_summary_csv(all_summaries, summary_path)
        logger.info("Summary saved to %s", summary_path)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="LLM Inference Benchmark Runner")
    parser.add_argument("--dry-run", action="store_true", help="Validate config and print plan without API calls")
    parser.add_argument("--platform", choices=["simplismart", "fireworks", "both"], default="both")
    parser.add_argument("--priority", choices=["p0", "all"], default="p0")
    parser.add_argument("--scenarios", type=str, default=None, help="Comma-separated scenario IDs, e.g. E01,E02")
    args = parser.parse_args()

    asyncio.run(main(
        platform_filter=args.platform,
        priority_filter=args.priority,
        scenario_override=args.scenarios,
        dry_run=args.dry_run,
    ))
