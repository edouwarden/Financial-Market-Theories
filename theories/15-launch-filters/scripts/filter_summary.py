#!/usr/bin/env python3
"""Deduplicated launch-filter report.

The earlier report counted DEX rows, not tokens. A token with three pools was
counted three times, which inflated both the baseline and the apparent filter
lift. This script collapses the discovery data to one row per token address and
reports row-level and token-level metrics separately.

The filter is deliberately simple: `txns_5m = buys + sells >= 0.25`. The point
is to show that the apparent edge disappears after deduplication, not to sell a
strategy.

Usage:
    python3 scripts/filter_summary.py
    python3 scripts/filter_summary.py --threshold 0.25 --out results/filter_analysis_report.json
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DISCOVERY = ROOT / "data/raw/merged_new_data.json"
DEFAULT_WINNERS = ROOT / "data/sample/merged_success_data_filtered.json"
DEFAULT_OUT = ROOT / "results/filter_analysis_report.json"


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def token_address(row: dict) -> str:
    base = row.get("baseToken") or {}
    return (base.get("address") or row.get("token_address") or "").lower()


def txns_5m(row: dict) -> float:
    m5 = (row.get("txns") or {}).get("m5") or {}
    return float(m5.get("buys", 0) or 0) + float(m5.get("sells", 0) or 0)


def liquidity_usd(row: dict) -> float:
    return float((row.get("liquidity") or {}).get("usd", 0) or 0)


def dedupe(rows: list[dict]) -> tuple[dict[str, dict], dict[str, dict]]:
    """Return (primary-pool rows, first-row rows) keyed by token address.

    Primary pool = the pool with the highest USD liquidity. First-row is kept as
    a sensitivity check because the choice of representative pool can change
    the filter's coverage.
    """
    primary: dict[str, dict] = {}
    first: dict[str, dict] = {}
    for row in rows:
        address = token_address(row)
        if not address:
            continue
        first.setdefault(address, row)
        current = primary.get(address)
        if current is None or liquidity_usd(row) > liquidity_usd(current):
            primary[address] = row
    return primary, first


def filter_metrics(rows: dict[str, dict], winners: set[str], threshold: float) -> dict:
    selected = {address: row for address, row in rows.items() if txns_5m(row) >= threshold}
    wins = sum(1 for address in selected if address in winners)
    total = len(rows)
    filtered = len(selected)
    return {
        "filtered_tokens": filtered,
        "wins": wins,
        "winrate": round(100 * wins / filtered, 2) if filtered else 0.0,
        "coverage": round(100 * filtered / total, 2) if total else 0.0,
    }


def temporal_holdout(rows: dict[str, dict], winners: set[str], threshold: float) -> dict:
    ordered = sorted(rows.values(), key=lambda row: row.get("pairCreatedAt") or 0)
    cut = int(len(ordered) * 0.7)
    parts = {"early_70pct": ordered[:cut], "late_30pct": ordered[cut:]}
    result = {}
    for name, part in parts.items():
        addresses = {token_address(row): row for row in part if token_address(row)}
        metrics = filter_metrics(addresses, winners, threshold)
        baseline = 100 * sum(1 for address in addresses if address in winners) / len(addresses) if addresses else 0.0
        metrics["baseline"] = round(baseline, 2)
        metrics["lift_pp"] = round(metrics["winrate"] - baseline, 2)
        result[name] = metrics
    result["split"] = "70% earliest / 30% latest by pairCreatedAt"
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Deduplicated launch-filter report")
    parser.add_argument("--discovery", type=Path, default=DEFAULT_DISCOVERY)
    parser.add_argument("--winners", type=Path, default=DEFAULT_WINNERS)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--threshold", type=float, default=0.25)
    args = parser.parse_args()

    discovery_rows = load_json(args.discovery)
    winner_rows = load_json(args.winners)

    winners = {token_address(row) for row in winner_rows if token_address(row)}
    primary, first = dedupe(discovery_rows)

    matched_rows = sum(1 for row in discovery_rows if token_address(row) in winners)
    row_baseline = 100 * matched_rows / len(discovery_rows) if discovery_rows else 0.0
    token_baseline = 100 * len(winners) / len(primary) if primary else 0.0

    primary_metrics = filter_metrics(primary, winners, args.threshold)
    first_metrics = filter_metrics(first, winners, args.threshold)
    for metrics, baseline in ((primary_metrics, token_baseline), (first_metrics, token_baseline)):
        metrics["baseline"] = round(baseline, 2)
        metrics["lift_pp"] = round(metrics["winrate"] - baseline, 2)

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": {
            "discovery": str(args.discovery.relative_to(ROOT)),
            "winners": str(args.winners.relative_to(ROOT)),
        },
        "dedupe": {
            "key": "baseToken.address",
            "rule": "keep the pool with the highest liquidity.usd",
            "discovery_rows": len(discovery_rows),
            "unique_discovery_tokens": len(primary),
            "winner_rows": len(winner_rows),
            "unique_winner_tokens": len(winners),
            "matched_rows": matched_rows,
        },
        "data_overview": {
            "discovery_rows": len(discovery_rows),
            "unique_discovery_tokens": len(primary),
            "winner_rows": len(winner_rows),
            "unique_winner_tokens": len(winners),
            "matched_rows": matched_rows,
            "row_level_success_rate": round(row_baseline, 2),
            "token_level_success_rate": round(token_baseline, 2),
        },
        "filter": {
            "field": "txns_5m",
            "definition": "buys + sells in the first 5 minutes",
            "threshold": args.threshold,
            "primary_pool": primary_metrics,
            "first_row_sensitivity": first_metrics,
            "temporal_holdout": temporal_holdout(primary, winners, args.threshold),
        },
        "summary": {
            "total_tokens_analyzed": len(primary),
            "success_tokens_found": len(winners),
            "baseline_success_rate": round(token_baseline, 2),
            "best_filter_winrate": primary_metrics["winrate"],
            "improvement": primary_metrics["lift_pp"],
        },
        "interpretation": {
            "verdict": "negative",
            "why": (
                "The row-level +0.44 pp lift was a duplicate-pool artifact. "
                "After collapsing to one row per token, the filter selects almost "
                "the entire universe and the lift is about +0.1 pp, which is "
                "economically indistinguishable from zero after costs."
            ),
            "caveats": [
                "The 1.5x success label is retrospective and does not model a fixed holding horizon.",
                "The threshold was originally selected in-sample; the temporal split evaluates that fixed rule, not a full out-of-sample search.",
                "Fees, slippage, liquidity constraints, and multiple-testing correction are not modeled.",
            ],
        },
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print("Deduplicated launch-filter report")
    print(f"  discovery rows:      {len(discovery_rows):,}")
    print(f"  unique tokens:       {len(primary):,}")
    print(f"  unique winners:      {len(winners):,}")
    print(f"  row-level baseline:  {row_baseline:.2f}%")
    print(f"  token-level baseline:{token_baseline:.2f}%")
    print(f"  filter winrate:      {primary_metrics['winrate']:.2f}%")
    print(f"  coverage:            {primary_metrics['coverage']:.2f}%")
    print(f"  lift:                {primary_metrics['lift_pp']:+.2f} pp")
    print(f"  wrote:               {args.out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
