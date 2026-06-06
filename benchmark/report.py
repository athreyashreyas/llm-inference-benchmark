"""Report generation: comparison tables and charts from benchmark summary CSVs."""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Optional

import matplotlib
matplotlib.use("Agg")  # non-interactive backend for CI / headless
import matplotlib.pyplot as plt
import pandas as pd

logger = logging.getLogger(__name__)

RESULTS_DIR = Path(__file__).parent.parent / "data" / "results"
CHARTS_DIR = Path(__file__).parent.parent / "report" / "charts"


def find_latest_summary(platform: str) -> Optional[Path]:
    """Find the most recently created summary CSV for a platform."""
    candidates = sorted(RESULTS_DIR.glob("summary_*.csv"), key=lambda p: p.stat().st_mtime, reverse=True)
    for c in candidates:
        df = pd.read_csv(c)
        if (df["platform"] == platform).any():
            return c
    return None


def load_both_summaries() -> pd.DataFrame:
    """Load and concatenate summary data for both platforms."""
    frames = []
    for platform in ("simplismart", "fireworks"):
        path = find_latest_summary(platform)
        if path is None:
            logger.warning("No summary CSV found for %s. Skipping.", platform)
            continue
        df = pd.read_csv(path)
        frames.append(df[df["platform"] == platform])
    if not frames:
        raise FileNotFoundError("No summary CSVs found. Run the benchmark first.")
    return pd.concat(frames, ignore_index=True)


def print_markdown_table(df: pd.DataFrame) -> None:
    """Print a full markdown comparison table matching the vLLM benchmark output format."""
    print("\n## Benchmark Results: Simplismart vs Fireworks AI\n")

    # --- Throughput & request stats ---
    print("### Throughput & Request Stats\n")
    cols = [
        "platform", "scenario_id", "concurrency",
        "successful_requests", "success_rate",
        "benchmark_duration_s", "req_throughput",
        "output_tok_throughput", "total_tok_throughput",
        "total_input_tokens", "total_output_tokens",
        "cold_start_ttft_ms",
        "cost_per_1k_output_tokens", "estimated_total_cost_usd",
    ]
    labels = [
        "Platform", "Scenario", "Concurrency",
        "Successful Reqs", "Success %",
        "Duration (s)", "Req/s",
        "Out tok/s", "Total tok/s",
        "Total In Tokens", "Total Out Tokens",
        "Cold Start TTFT (ms)",
        "Cost/1K out ($)", "Est. Cost ($)",
    ]
    _print_table(df, cols, labels)

    # --- Latency metrics ---
    print("\n### Latency Metrics\n")
    cols = [
        "platform", "scenario_id", "concurrency",
        "mean_ttft_ms", "p50_ttft_ms", "p95_ttft_ms", "p99_ttft_ms",
        "mean_tpot_ms", "p50_tpot_ms", "p99_tpot_ms",
        "mean_itl_ms", "p50_itl_ms", "p99_itl_ms",
        "mean_e2e_ms", "p95_e2e_ms", "p99_e2e_ms",
        "mean_tps",
    ]
    labels = [
        "Platform", "Scenario", "Concurrency",
        "Mean TTFT", "p50 TTFT", "p95 TTFT", "p99 TTFT",
        "Mean TPOT", "p50 TPOT", "p99 TPOT",
        "Mean ITL", "p50 ITL", "p99 ITL",
        "Mean E2E", "p95 E2E", "p99 E2E",
        "Mean TPS",
    ]
    _print_table(df, cols, labels)


def _print_table(df: pd.DataFrame, cols: list, labels: list) -> None:
    available = [c for c in cols if c in df.columns]
    available_labels = [labels[cols.index(c)] for c in available]
    sub = df[available].copy()
    header = "| " + " | ".join(available_labels) + " |"
    sep = "| " + " | ".join(["---"] * len(available_labels)) + " |"
    print(header)
    print(sep)
    for _, row in sub.iterrows():
        print("| " + " | ".join(str(round(v, 2) if isinstance(v, float) else v) for v in row) + " |")
    print()


def _grouped_bar(df: pd.DataFrame, metric: str, ylabel: str, title: str, out_path: Path) -> None:
    """Draw a grouped bar chart by scenario, grouped by platform."""
    if metric not in df.columns:
        logger.warning("Metric %s not in summary — skipping chart.", metric)
        return
    platforms = df["platform"].unique()
    scenarios = sorted(df["scenario_id"].unique())
    x = range(len(scenarios))
    width = 0.35

    fig, ax = plt.subplots(figsize=(10, 5))
    for i, platform in enumerate(platforms):
        pdata = df[df["platform"] == platform].set_index("scenario_id")
        vals = [pdata.loc[s, metric] if s in pdata.index else float("nan") for s in scenarios]
        offset = (i - len(platforms) / 2 + 0.5) * width
        ax.bar([xi + offset for xi in x], vals, width, label=platform)

    ax.set_xticks(list(x))
    ax.set_xticklabels(scenarios)
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.legend()
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    logger.info("Chart saved: %s", out_path)


def plot_ttft_comparison(df: pd.DataFrame) -> None:
    _grouped_bar(df, "mean_ttft_ms", "Mean TTFT (ms)",
                 "Time to First Token — Simplismart vs Fireworks",
                 CHARTS_DIR / "ttft_comparison.png")


def plot_tpot_comparison(df: pd.DataFrame) -> None:
    _grouped_bar(df, "mean_tpot_ms", "Mean TPOT (ms)",
                 "Time Per Output Token — Simplismart vs Fireworks",
                 CHARTS_DIR / "tpot_comparison.png")


def plot_itl_comparison(df: pd.DataFrame) -> None:
    _grouped_bar(df, "mean_itl_ms", "Mean ITL (ms)",
                 "Inter-Token Latency — Simplismart vs Fireworks",
                 CHARTS_DIR / "itl_comparison.png")


def plot_throughput_comparison(df: pd.DataFrame) -> None:
    _grouped_bar(df, "output_tok_throughput", "Output tokens/sec",
                 "Output Token Throughput — Simplismart vs Fireworks",
                 CHARTS_DIR / "throughput_comparison.png")


def plot_latency_concurrency(df: pd.DataFrame) -> None:
    """Line chart of mean E2E latency vs concurrency, one line per platform."""
    fig, ax = plt.subplots(figsize=(8, 5))
    for platform in df["platform"].unique():
        pdata = df[df["platform"] == platform].groupby("concurrency")["mean_e2e_ms"].mean().reset_index()
        ax.plot(pdata["concurrency"], pdata["mean_e2e_ms"], marker="o", label=platform)
    ax.set_xlabel("Concurrency")
    ax.set_ylabel("Mean E2E Latency (ms)")
    ax.set_title("Latency vs Concurrency — Simplismart vs Fireworks")
    ax.legend()
    fig.tight_layout()
    path = CHARTS_DIR / "latency_concurrency.png"
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=150)
    plt.close(fig)
    logger.info("Chart saved: %s", path)


def plot_p99_comparison(df: pd.DataFrame) -> None:
    """Side-by-side p99 TTFT, TPOT, ITL for each platform."""
    metrics = [("p99_ttft_ms", "p99 TTFT"), ("p99_tpot_ms", "p99 TPOT"), ("p99_itl_ms", "p99 ITL")]
    available = [(m, l) for m, l in metrics if m in df.columns]
    if not available:
        return

    fig, axes = plt.subplots(1, len(available), figsize=(5 * len(available), 5))
    if len(available) == 1:
        axes = [axes]

    for ax, (metric, label) in zip(axes, available):
        for platform in df["platform"].unique():
            pdata = df[df["platform"] == platform].set_index("scenario_id")
            scenarios = sorted(pdata.index)
            vals = [pdata.loc[s, metric] if s in pdata.index else float("nan") for s in scenarios]
            ax.plot(scenarios, vals, marker="o", label=platform)
        ax.set_title(label)
        ax.set_ylabel("ms")
        ax.tick_params(axis="x", rotation=45)
        ax.legend(fontsize=8)

    fig.suptitle("p99 Tail Latency Comparison")
    fig.tight_layout()
    path = CHARTS_DIR / "p99_comparison.png"
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=150)
    plt.close(fig)
    logger.info("Chart saved: %s", path)


def print_narrative(df: pd.DataFrame) -> None:
    """Print a short narrative interpretation of the results."""
    smrt = df[df["platform"] == "simplismart"]
    fw = df[df["platform"] == "fireworks"]

    def safe_mean(series):
        return series.mean() if not series.empty else float("nan")

    smrt_ttft  = safe_mean(smrt["mean_ttft_ms"])
    fw_ttft    = safe_mean(fw["mean_ttft_ms"])
    smrt_tpot  = safe_mean(smrt["mean_tpot_ms"]) if "mean_tpot_ms" in smrt else float("nan")
    fw_tpot    = safe_mean(fw["mean_tpot_ms"]) if "mean_tpot_ms" in fw else float("nan")
    smrt_tps   = safe_mean(smrt["output_tok_throughput"]) if "output_tok_throughput" in smrt else float("nan")
    fw_tps     = safe_mean(fw["output_tok_throughput"]) if "output_tok_throughput" in fw else float("nan")
    smrt_cost  = safe_mean(smrt["cost_per_1k_output_tokens"]) if "cost_per_1k_output_tokens" in smrt else float("nan")
    fw_cost    = safe_mean(fw["cost_per_1k_output_tokens"]) if "cost_per_1k_output_tokens" in fw else float("nan")

    faster_ttft  = "Simplismart" if smrt_ttft < fw_ttft else "Fireworks AI"
    faster_tpot  = "Simplismart" if smrt_tpot < fw_tpot else "Fireworks AI"
    higher_tps   = "Simplismart" if smrt_tps > fw_tps else "Fireworks AI"
    cheaper      = "Simplismart" if smrt_cost < fw_cost else "Fireworks AI"

    print("\n## Narrative Summary\n")
    print(
        f"**Responsiveness (TTFT):** {faster_ttft} delivered lower mean TTFT "
        f"({min(smrt_ttft, fw_ttft):.0f} ms vs {max(smrt_ttft, fw_ttft):.0f} ms).\n\n"
        f"**Streaming smoothness (TPOT):** {faster_tpot} had lower mean time per output token "
        f"({min(smrt_tpot, fw_tpot):.2f} ms vs {max(smrt_tpot, fw_tpot):.2f} ms).\n\n"
        f"**Throughput:** {higher_tps} achieved higher output token throughput "
        f"({max(smrt_tps, fw_tps):.1f} tok/s vs {min(smrt_tps, fw_tps):.1f} tok/s).\n\n"
        f"**Cost:** {cheaper} is cheaper per 1K output tokens "
        f"(${min(smrt_cost, fw_cost):.4f} vs ${max(smrt_cost, fw_cost):.4f}).\n\n"
        f"These numbers reflect a single benchmark session on dedicated H100 GPU endpoints. "
        f"Results are indicative and may vary with traffic patterns and platform load."
    )
    print()


def generate_report() -> None:
    """Load summaries, print tables, generate all charts, print narrative."""
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    df = load_both_summaries()
    print_markdown_table(df)
    plot_ttft_comparison(df)
    plot_tpot_comparison(df)
    plot_itl_comparison(df)
    plot_throughput_comparison(df)
    plot_latency_concurrency(df)
    plot_p99_comparison(df)
    print_narrative(df)
    print(f"Charts written to {CHARTS_DIR}/")


if __name__ == "__main__":
    generate_report()
