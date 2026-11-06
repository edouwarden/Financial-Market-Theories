#!/usr/bin/env python3
"""Summarise a committed L2 snapshot and flag large visible levels.

This is the offline part of theory 10. It does not test wall absorption,
cancellation, or exchange fee incentives. It answers a narrower question:
given one order-book snapshot, where is the visible liquidity and which levels
are unusually large relative to the rest of the book?

Example:
    python3 scripts/wall_report.py
"""

from __future__ import annotations

import argparse
import json
import statistics
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parent
DEFAULT_INPUT = PROJECT / "data" / "sample" / "orderbook.json"
DEFAULT_OUTPUT = PROJECT / "results" / "wall_snapshot.json"
DEFAULT_CHART = PROJECT / "results" / "wall_depth.png"


def load_snapshot(path: Path) -> tuple[str, dict, dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit(f"{path}: expected a JSON object")

    ticker = payload.get("ticker") if isinstance(payload.get("ticker"), dict) else payload
    depth = payload.get("depth") if isinstance(payload.get("depth"), dict) else payload
    if not isinstance(depth.get("bids"), list) or not isinstance(depth.get("asks"), list):
        raise SystemExit(f"{path}: missing bids/asks arrays")

    symbol = str(payload.get("symbol") or ticker.get("symbol") or "UNKNOWN")
    return symbol, ticker, depth


def levels(depth: dict, side: str) -> list[tuple[float, float]]:
    out = []
    for level in depth.get(side, []):
        if not isinstance(level, (list, tuple)) or len(level) < 2:
            continue
        try:
            out.append((float(level[0]), float(level[1])))
        except (TypeError, ValueError):
            continue
    out.sort(key=lambda item: item[0], reverse=(side == "bids"))
    return out


def find_walls(
    rows: list[tuple[float, float]],
    median_volume: float,
    min_volume: float,
    multiple: float,
) -> list[dict]:
    threshold = max(min_volume, median_volume * multiple)
    walls = [
        {
            "price": price,
            "volume": volume,
            "notional": round(price * volume, 2),
            "multipleOfMedian": round(volume / median_volume, 2) if median_volume else None,
        }
        for price, volume in rows
        if volume >= threshold
    ]
    walls.sort(key=lambda item: item["volume"], reverse=True)
    return walls[:10]


def human_price(value: float) -> str:
    return f"{value:,.2f}"


def display_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(PROJECT))
    except ValueError:
        return str(path)


def draw_chart(
    symbol: str,
    bids: list[tuple[float, float]],
    asks: list[tuple[float, float]],
    bid_walls: list[dict],
    ask_walls: list[dict],
    output: Path,
) -> None:
    width, height = 1200, 700
    margin_left, margin_right = 80, 40
    margin_top, margin_bottom = 70, 70
    plot_w, plot_h = width - margin_left - margin_right, height - margin_top - margin_bottom

    bid_cum = []
    total = 0.0
    for price, volume in bids:
        total += volume
        bid_cum.append((price, total))
    ask_cum = []
    total = 0.0
    for price, volume in asks:
        total += volume
        ask_cum.append((price, total))

    prices = [p for p, _ in bid_cum] + [p for p, _ in ask_cum]
    if not prices:
        raise SystemExit("no price levels to chart")
    min_price, max_price = min(prices), max(prices)
    max_cum = max(
        [v for _, v in bid_cum] + [v for _, v in ask_cum] + [1.0]
    )

    canvas = Image.new("RGB", (width, height), (248, 248, 246))
    draw = ImageDraw.Draw(canvas)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)
        title_font = ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 20
        )
    except OSError:
        font = ImageFont.load_default()
        title_font = font

    def x_of(price: float) -> float:
        if max_price == min_price:
            return margin_left + plot_w / 2
        return margin_left + (price - min_price) / (max_price - min_price) * plot_w

    def y_of(cum: float) -> float:
        return margin_top + plot_h - (cum / max_cum) * plot_h

    draw.text(
        (margin_left, 22),
        f"{symbol} visible depth — {len(bids)} bids / {len(asks)} asks",
        fill=(25, 25, 25),
        font=title_font,
    )
    draw.text(
        (margin_left, 46),
        "Cumulative size from the snapshot; wall marks are threshold flags, not predictions.",
        fill=(85, 85, 85),
        font=font,
    )

    # Axes and grid.
    draw.rectangle(
        [margin_left, margin_top, margin_left + plot_w, margin_top + plot_h],
        outline=(180, 180, 180),
    )
    for i in range(5):
        y = margin_top + plot_h * i / 4
        draw.line([(margin_left, y), (margin_left + plot_w, y)], fill=(226, 226, 222))
        label = f"{max_cum * (4 - i) / 4:,.0f}"
        draw.text((12, y - 8), label, fill=(95, 95, 95), font=font)

    bid_points = [(x_of(p), y_of(v)) for p, v in bid_cum]
    ask_points = [(x_of(p), y_of(v)) for p, v in ask_cum]
    if len(bid_points) > 1:
        draw.line(bid_points, fill=(40, 130, 80), width=3)
    if len(ask_points) > 1:
        draw.line(ask_points, fill=(180, 60, 60), width=3)

    for wall in bid_walls:
        x = x_of(wall["price"])
        y = y_of(
            next((v for p, v in bid_cum if p == wall["price"]), 0.0)
        )
        draw.ellipse([x - 5, y - 5, x + 5, y + 5], fill=(20, 90, 55))
        draw.text((x + 7, y - 8), f"{wall['volume']:.1f}", fill=(20, 90, 55), font=font)
    for wall in ask_walls:
        x = x_of(wall["price"])
        y = y_of(
            next((v for p, v in ask_cum if p == wall["price"]), 0.0)
        )
        draw.ellipse([x - 5, y - 5, x + 5, y + 5], fill=(140, 30, 30))
        draw.text((x + 7, y - 8), f"{wall['volume']:.1f}", fill=(140, 30, 30), font=font)

    draw.text(
        (margin_left, height - 42),
        f"price range {human_price(min_price)} – {human_price(max_price)}  ·  "
        f"green = bids, red = asks  ·  labels = wall size (BTC)",
        fill=(85, 85, 85),
        font=font,
    )

    output.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output, format="PNG", optimize=True)
    print(f"wrote {output}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--chart", type=Path, default=DEFAULT_CHART)
    parser.add_argument("--min-wall", type=float, default=5.0, help="minimum wall size in BTC")
    parser.add_argument("--median-multiple", type=float, default=3.0)
    parser.add_argument("--no-chart", action="store_true")
    args = parser.parse_args()

    symbol, ticker, depth = load_snapshot(args.input)
    bids = levels(depth, "bids")
    asks = levels(depth, "asks")
    if not bids or not asks:
        raise SystemExit("snapshot has no usable bids or asks")

    best_bid = bids[0][0]
    best_ask = asks[0][0]
    mid = (best_bid + best_ask) / 2
    spread = best_ask - best_bid
    bid_volumes = [v for _, v in bids]
    ask_volumes = [v for _, v in asks]
    median_volume = statistics.median(bid_volumes + ask_volumes)

    bid_walls = find_walls(
        bids, median_volume, args.min_wall, args.median_multiple
    )
    ask_walls = find_walls(
        asks, median_volume, args.min_wall, args.median_multiple
    )

    captured = ticker.get("time") or depth.get("E")
    captured_iso = (
        datetime.fromtimestamp(captured / 1000, tz=timezone.utc).isoformat()
        if isinstance(captured, (int, float))
        else None
    )

    report = {
        "source": display_path(args.input),
        "symbol": symbol,
        "capturedAt": captured_iso,
        "tickerPrice": float(ticker["price"]) if "price" in ticker else None,
        "summary": {
            "bestBid": best_bid,
            "bestAsk": best_ask,
            "mid": round(mid, 4),
            "spread": round(spread, 4),
            "spreadBps": round(spread / mid * 10_000, 2) if mid else None,
            "bidLevels": len(bids),
            "askLevels": len(asks),
            "bidVolume": round(sum(bid_volumes), 4),
            "askVolume": round(sum(ask_volumes), 4),
            "medianLevelVolume": round(median_volume, 4),
        },
        "wallRule": {
            "minVolumeBtc": args.min_wall,
            "medianMultiple": args.median_multiple,
            "description": "volume >= max(minVolumeBtc, medianMultiple * median level volume)",
        },
        "bidWalls": bid_walls,
        "askWalls": ask_walls,
        "caveats": [
            "One snapshot, not a time series.",
            "Visible size is not executed size; spoofing and cancellation are not observed.",
            "The report does not test exchange fee incentives or wall absorption.",
        ],
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {args.output}")
    print(
        f"mid {mid:,.2f}  spread {spread:,.2f} ({report['summary']['spreadBps']} bps)  "
        f"walls {len(bid_walls)} bid / {len(ask_walls)} ask"
    )

    if not args.no_chart:
        draw_chart(symbol, bids, asks, bid_walls, ask_walls, args.chart)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
