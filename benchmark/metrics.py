"""Metrics aggregation and CSV persistence."""

from __future__ import annotations

import csv
import logging
from pathlib import Path
from typing import List, Dict, Any

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

RAW_CSV_FIELDS = [
    "run_id", "platform", "scenario_id", "concurrency", "prompt_id",
    "benchmark_duration_s", "cold_start_ttft_ms",
    "ttft_ms", "tpot_ms", "itl_ms", "e2e_ms",
    "input_tokens", "output_tokens", "tokens_per_sec",
    "status", "error_type", "timestamp",
]

# Pricing (output tokens) — update if platform pricing changes
COST_PER_M_OUTPUT_TOKENS: dict[str, float] = {
    "simplismart": 0.10,   # Gemma 3 4B Instruct on Simplismart (dedicated H100)
    "fireworks":   0.10,   # Gemma 3 4B Instruct on Fireworks (dedicated H100)
}

SUMMARY_CSV_FIELDS = [
    "platform", "scenario_id", "concurrency",
    # Request counts
    "n_requests", "successful_requests", "success_rate",
    # Throughput (requires benchmark_duration_s)
    "benchmark_duration_s",
    "req_throughput",            # req/s
    "output_tok_throughput",     # output tok/s
    "total_tok_throughput",      # (input + output) tok/s
    "total_input_tokens",
    "total_output_tokens",
    # Cost efficiency
    "cost_per_1k_output_tokens", # USD per 1K output tokens
    "estimated_total_cost_usd",  # USD cost for this scenario run
    # Cold start
    "cold_start_ttft_ms",        # TTFT of first-ever request — may include GPU spin-up
    # TTFT
    "mean_ttft_ms", "p50_ttft_ms", "p95_ttft_ms", "p99_ttft_ms",
    # TPOT
    "mean_tpot_ms", "p50_tpot_ms", "p95_tpot_ms", "p99_tpot_ms",
    # ITL
    "mean_itl_ms", "p50_itl_ms", "p95_itl_ms", "p99_itl_ms",
    # E2E
    "mean_e2e_ms", "p95_e2e_ms", "p99_e2e_ms",
    # Per-request TPS
    "mean_tps", "std_tps",
]


def compute_summary(
    results: List[Dict[str, Any]],
    platform: str = "",
    cold_start_ttft_ms: float | None = None,
) -> Dict[str, Any]:
    """Compute aggregate metrics from a list of raw result dicts.

    Matches the vLLM benchmark output format:
      - Successful requests, benchmark duration, total tokens
      - Request throughput (req/s), output tok/s, total tok/s
      - Cost per 1K output tokens + estimated total cost
      - Cold start TTFT (first request — may include GPU spin-up time)
      - TTFT / TPOT / ITL — mean, median (p50), p95, p99
    """
    total = len(results)
    successes = [r for r in results if r.get("status") == "success"]
    n_success = len(successes)
    success_rate = (n_success / total * 100) if total > 0 else 0.0

    # benchmark_duration_s: same value stamped on every row — take max
    durations = [r["benchmark_duration_s"] for r in results if r.get("benchmark_duration_s")]
    benchmark_duration_s = max(durations) if durations else None

    # Token totals
    total_input  = sum((r.get("input_tokens")  or 0) for r in successes)
    total_output = sum((r.get("output_tokens") or 0) for r in successes)

    # Throughput metrics
    req_throughput        = round(n_success / benchmark_duration_s, 2) if benchmark_duration_s else float("nan")
    output_tok_throughput = round(total_output / benchmark_duration_s, 2) if benchmark_duration_s else float("nan")
    total_tok_throughput  = round((total_input + total_output) / benchmark_duration_s, 2) if benchmark_duration_s else float("nan")

    # Cost efficiency
    rate = COST_PER_M_OUTPUT_TOKENS.get(platform, 0.20)
    cost_per_1k = round(rate / 1000, 6)
    estimated_cost = round((total_output / 1_000_000) * rate, 6)

    ttft_vals = [r["ttft_ms"]        for r in successes if r.get("ttft_ms")        is not None]
    tpot_vals = [r["tpot_ms"]        for r in successes if r.get("tpot_ms")        is not None]
    itl_vals  = [r["itl_ms"]         for r in successes if r.get("itl_ms")         is not None]
    e2e_vals  = [r["e2e_ms"]         for r in successes if r.get("e2e_ms")         is not None]
    tps_vals  = [r["tokens_per_sec"] for r in successes if r.get("tokens_per_sec") is not None]

    def mean(arr: list) -> float:
        return round(float(np.mean(arr)), 2) if arr else float("nan")

    def pct(arr: list, p: float) -> float:
        return round(float(np.percentile(arr, p)), 2) if arr else float("nan")

    return {
        "n_requests":                total,
        "successful_requests":       n_success,
        "success_rate":              round(success_rate, 2),
        "benchmark_duration_s":      round(benchmark_duration_s, 3) if benchmark_duration_s else float("nan"),
        "req_throughput":            req_throughput,
        "output_tok_throughput":     output_tok_throughput,
        "total_tok_throughput":      total_tok_throughput,
        "total_input_tokens":        total_input,
        "total_output_tokens":       total_output,
        "cost_per_1k_output_tokens": cost_per_1k,
        "estimated_total_cost_usd":  estimated_cost,
        "cold_start_ttft_ms":        cold_start_ttft_ms,
        # TTFT
        "mean_ttft_ms":  mean(ttft_vals),
        "p50_ttft_ms":   pct(ttft_vals, 50),
        "p95_ttft_ms":   pct(ttft_vals, 95),
        "p99_ttft_ms":   pct(ttft_vals, 99),
        # TPOT
        "mean_tpot_ms":  mean(tpot_vals),
        "p50_tpot_ms":   pct(tpot_vals, 50),
        "p95_tpot_ms":   pct(tpot_vals, 95),
        "p99_tpot_ms":   pct(tpot_vals, 99),
        # ITL
        "mean_itl_ms":   mean(itl_vals),
        "p50_itl_ms":    pct(itl_vals, 50),
        "p95_itl_ms":    pct(itl_vals, 95),
        "p99_itl_ms":    pct(itl_vals, 99),
        # E2E
        "mean_e2e_ms":   mean(e2e_vals),
        "p95_e2e_ms":    pct(e2e_vals, 95),
        "p99_e2e_ms":    pct(e2e_vals, 99),
        # Per-request throughput
        "mean_tps":      mean(tps_vals),
        "std_tps":       round(float(np.std(tps_vals)), 2) if tps_vals else float("nan"),
    }


def save_raw_csv(results: List[Dict[str, Any]], path: Path) -> None:
    """Append raw results to a CSV file, creating it with headers if new."""
    path.parent.mkdir(parents=True, exist_ok=True)
    write_header = not path.exists()
    with open(path, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=RAW_CSV_FIELDS, extrasaction="ignore")
        if write_header:
            writer.writeheader()
        writer.writerows(results)
    logger.info("Raw results written to %s (%d rows)", path, len(results))


def save_summary_csv(summaries: List[Dict[str, Any]], path: Path) -> pd.DataFrame:
    """Write summary metrics to CSV and return as a DataFrame."""
    path.parent.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(summaries, columns=SUMMARY_CSV_FIELDS)
    df.to_csv(path, index=False)
    logger.info("Summary written to %s", path)
    return df


def load_summary_csv(path: Path) -> pd.DataFrame:
    """Load a summary CSV from disk."""
    return pd.read_csv(path)
