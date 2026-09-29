import time
from pathlib import Path

from app.backend.services.orchestrator import process_interaction_event
from app.ml.data import load_and_prepare_data

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data" / "sample"

# Cost assumptions for product framing (e.g., standard LLM API pricing per call)
ESTIMATED_LLM_COST_PER_CALL_USD = 0.0025  # ~$2.50 per 1k complex calls
ESTIMATED_FASTPATH_COST_PER_CALL_USD = 0.00001  # Local compute expense


def run_benchmark(sample_size: int = 100):
    """
    Benchmark speed, throughput, and projected cost
    savings across hybrid routing paths.
    """
    print(f"Loading benchmark dataset from {DATA_DIR}...")
    df = load_and_prepare_data(DATA_DIR)

    if len(df) > sample_size:
        df = df.sample(n=sample_size, random_state=42)

    fast_path_count = 0
    fallback_count = 0

    fast_path_latencies = []
    fallback_latencies = []

    print(f"\nRunning benchmark on {len(df)} sample interactions...\n")
    total_start = time.perf_counter()

    for idx, row in df.iterrows():
        payload = {
            "full_text": row.get("rich_text", ""),
            "channel": row.get("channel", "chat"),
            "detected_sentiment": row.get("detected_sentiment", "neutral"),
            "duration_seconds": row.get("duration_seconds", 0.0),
            "wait_time_seconds": row.get("wait_time_seconds", 0.0),
            "sentiment_score": row.get("sentiment_score", 0.0),
            "has_past_complaint": row.get("has_past_complaint", False),
        }

        result = process_interaction_event(payload)

        if result["source"] == "DETERMINISTIC_FAST_PATH":
            fast_path_count += 1
            fast_path_latencies.append(result["latency_ms"])
        else:
            fallback_count += 1
            fallback_latencies.append(result["latency_ms"])

    total_time = time.perf_counter() - total_start

    # Metrics calculation
    fast_path_ratio = (fast_path_count / len(df)) * 100
    avg_fast_path_latency = (
        sum(fast_path_latencies) / len(fast_path_latencies)
        if fast_path_latencies
        else 0
    )
    avg_fallback_latency = (
        sum(fallback_latencies) / len(fallback_latencies) if fallback_latencies else 0
    )

    # Cost calculations
    unoptimized_cost = len(df) * ESTIMATED_LLM_COST_PER_CALL_USD
    hybrid_cost = (fast_path_count * ESTIMATED_FASTPATH_COST_PER_CALL_USD) + (
        fallback_count * ESTIMATED_LLM_COST_PER_CALL_USD
    )
    cost_savings = unoptimized_cost - hybrid_cost
    cost_reduction_pct = (
        (cost_savings / unoptimized_cost) * 100 if unoptimized_cost > 0 else 0
    )

    print("==================================================")
    print("         HYBRID ROUTER BENCHMARK REPORT           ")
    print("==================================================")
    print(f"Total Interactions Evaluated : {len(df)}")
    print(f"Deterministic Fast-Path Hits : {fast_path_count} ({fast_path_ratio:.1f}%)")
    print(
        f"LLM Fallback Route Hits     : {fallback_count} ({100 - fast_path_ratio:.1f}%)"
    )
    print("--------------------------------------------------")
    print(f"Avg Fast-Path Latency       : {avg_fast_path_latency:.2f} ms")
    print(f"Avg LLM Fallback Latency     : {avg_fallback_latency:.2f} ms")
    print(f"Total Execution Time         : {total_time:.2f} s")
    print("--------------------------------------------------")
    print(f"Est. Full LLM Route Cost    : ${unoptimized_cost:.4f}")
    print(f"Est. Hybrid Route Cost      : ${hybrid_cost:.4f}")
    print(
        f"Projected Cost Savings      : ${cost_savings:.4f} ({cost_reduction_pct:.1f}%"
        " reduction)"
    )
    print("==================================================")


if __name__ == "__main__":
    run_benchmark()
