"""Unit tests for the benchmark modules. Zero real API calls — all mocked."""

from __future__ import annotations

import asyncio
import io
import sys
import time
import unittest
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

# Make sure the project root is on the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from benchmark.metrics import compute_summary
from benchmark.prompts import get_prompts_by_type, load_prompts, sample_prompts


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_result(status="success", ttft_ms=80.0, e2e_ms=500.0, out_tokens=40, in_tokens=10) -> Dict[str, Any]:
    tps = out_tokens / (e2e_ms / 1000) if e2e_ms > 0 else None
    return {
        "ttft_ms": ttft_ms,
        "e2e_ms": e2e_ms,
        "input_tokens": in_tokens,
        "output_tokens": out_tokens,
        "tokens_per_sec": tps,
        "status": status,
        "error_type": None,
    }


# ---------------------------------------------------------------------------
# Prompt loading tests
# ---------------------------------------------------------------------------


class TestPromptLoading(unittest.TestCase):
    def test_loads_30_prompts(self):
        prompts = load_prompts()
        self.assertEqual(len(prompts), 30)

    def test_prompt_types_present(self):
        prompts = load_prompts()
        types = {p["type"] for p in prompts}
        self.assertSetEqual(types, {"short", "medium", "long"})

    def test_short_count(self):
        short = get_prompts_by_type("short")
        self.assertEqual(len(short), 15)

    def test_medium_count(self):
        medium = get_prompts_by_type("medium")
        self.assertEqual(len(medium), 10)

    def test_long_count(self):
        long = get_prompts_by_type("long")
        self.assertEqual(len(long), 5)

    def test_all_prompts_have_text(self):
        for p in load_prompts():
            self.assertIn("text", p)
            self.assertGreater(len(p["text"]), 5)

    def test_all_prompts_have_id(self):
        for p in load_prompts():
            self.assertIn("id", p)

    def test_sample_prompts_count(self):
        sampled = sample_prompts("short", 5, seed=42)
        self.assertEqual(len(sampled), 5)

    def test_sample_prompts_correct_type(self):
        sampled = sample_prompts("medium", 3, seed=0)
        for p in sampled:
            self.assertEqual(p["type"], "medium")


# ---------------------------------------------------------------------------
# Metrics computation tests
# ---------------------------------------------------------------------------


class TestComputeSummary(unittest.TestCase):
    def test_success_rate_all_success(self):
        results = [make_result() for _ in range(10)]
        summary = compute_summary(results)
        self.assertEqual(summary["success_rate"], 100.0)
        self.assertEqual(summary["n_requests"], 10)

    def test_success_rate_mixed(self):
        results = [make_result()] * 8 + [make_result(status="error")] * 2
        summary = compute_summary(results)
        self.assertAlmostEqual(summary["success_rate"], 80.0)

    def test_ttft_mean_calculation(self):
        results = [make_result(ttft_ms=100.0), make_result(ttft_ms=200.0)]
        summary = compute_summary(results)
        self.assertAlmostEqual(summary["mean_ttft_ms"], 150.0)

    def test_e2e_mean_calculation(self):
        results = [make_result(e2e_ms=400.0), make_result(e2e_ms=600.0)]
        summary = compute_summary(results)
        self.assertAlmostEqual(summary["mean_e2e_ms"], 500.0)

    def test_tps_calculation(self):
        # 40 tokens / 0.5 s = 80 tps
        result = make_result(out_tokens=40, e2e_ms=500.0)
        summary = compute_summary([result])
        self.assertAlmostEqual(summary["mean_tps"], 80.0)

    def test_percentiles_present(self):
        results = [make_result(ttft_ms=float(i * 10)) for i in range(1, 11)]
        summary = compute_summary(results)
        self.assertIn("p50_ttft_ms", summary)
        self.assertIn("p95_ttft_ms", summary)
        self.assertIn("p99_ttft_ms", summary)

    def test_empty_results(self):
        summary = compute_summary([])
        self.assertEqual(summary["n_requests"], 0)
        self.assertEqual(summary["success_rate"], 0.0)

    def test_errors_excluded_from_latency(self):
        results = [make_result(status="error", ttft_ms=9999.0) for _ in range(5)]
        summary = compute_summary(results)
        import math
        self.assertTrue(math.isnan(summary["mean_ttft_ms"]))

    def test_p95_higher_than_p50(self):
        results = [make_result(ttft_ms=float(i)) for i in range(1, 101)]
        summary = compute_summary(results)
        self.assertGreater(summary["p95_ttft_ms"], summary["p50_ttft_ms"])


# ---------------------------------------------------------------------------
# Error handling tests
# ---------------------------------------------------------------------------


class TestErrorHandling(unittest.TestCase):
    def test_all_errors_gives_zero_success_rate(self):
        results = [make_result(status="error") for _ in range(5)]
        summary = compute_summary(results)
        self.assertEqual(summary["success_rate"], 0.0)

    def test_partial_errors(self):
        results = [make_result()] * 7 + [make_result(status="error")] * 3
        summary = compute_summary(results)
        self.assertAlmostEqual(summary["success_rate"], 70.0)


# ---------------------------------------------------------------------------
# Dry-run test (no real API calls)
# ---------------------------------------------------------------------------


class TestDryRun(unittest.TestCase):
    @patch("benchmark.runner.AsyncOpenAI")
    def test_dry_run_makes_no_api_calls(self, mock_openai_cls):
        """Verify that --dry-run mode does not instantiate an AsyncOpenAI client."""
        import os
        with patch.dict(os.environ, {
            "SIMPLISMART_API_KEY": "test_key",
            "SIMPLISMART_BASE_URL": "https://api.simplismart.ai/v1",
            "SIMPLISMART_MODEL_ID": "gemma-3-4b-it",
            "FIREWORKS_API_KEY": "test_key",
            "FIREWORKS_MODEL_ID": "accounts/fireworks/models/gemma-3-4b-it",
        }):
            from benchmark.runner import main
            asyncio.run(main(platform_filter="both", priority_filter="p0", dry_run=True))
        # AsyncOpenAI should never be called in dry-run mode
        mock_openai_cls.assert_not_called()

    @patch("benchmark.runner.AsyncOpenAI")
    def test_dry_run_prints_plan(self, mock_openai_cls):
        """Verify dry-run prints scenario plan to stdout."""
        import os
        captured = io.StringIO()
        with patch.dict(os.environ, {
            "SIMPLISMART_API_KEY": "test_key",
            "SIMPLISMART_BASE_URL": "https://api.simplismart.ai/v1",
            "SIMPLISMART_MODEL_ID": "gemma-3-4b-it",
            "FIREWORKS_API_KEY": "test_key",
            "FIREWORKS_MODEL_ID": "accounts/fireworks/models/gemma-3-4b-it",
        }), patch("sys.stdout", captured):
            from benchmark.runner import main
            asyncio.run(main(platform_filter="simplismart", priority_filter="p0", dry_run=True))
        output = captured.getvalue()
        self.assertIn("DRY RUN", output)


# ---------------------------------------------------------------------------
# TTFT calculation correctness
# ---------------------------------------------------------------------------


class TestTTFTCalculation(unittest.TestCase):
    def test_ttft_is_less_than_e2e(self):
        result = make_result(ttft_ms=80.0, e2e_ms=500.0)
        self.assertLess(result["ttft_ms"], result["e2e_ms"])

    def test_tps_formula(self):
        # tokens_per_sec = output_tokens / (e2e_ms / 1000)
        out_tokens = 50
        e2e_ms = 1000.0
        expected_tps = out_tokens / (e2e_ms / 1000)
        result = make_result(out_tokens=out_tokens, e2e_ms=e2e_ms)
        self.assertAlmostEqual(result["tokens_per_sec"], expected_tps)


if __name__ == "__main__":
    unittest.main()
