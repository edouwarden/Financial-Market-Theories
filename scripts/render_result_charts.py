#!/usr/bin/env python3
"""Render the committed result charts with Pillow.

The charts are presentation artifacts built from committed JSON, so they can be
regenerated without network access:

    python3 scripts/render_result_charts.py

Each function writes one PNG next to the data it summarises. The script does not
compute new statistics; it only reads the JSON files listed below.
"""

from __future__ import annotations

import json
import math
import statistics
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
OUT_BG = (248, 248, 246)
INK = (28, 28, 28)
MUTED = (100, 100, 100)
GRID = (225, 225, 221)
GREEN = (39, 128, 82)
RED = (176, 58, 58)
BLUE = (53, 103, 172)
ORANGE = (194, 120, 42)
PURPLE = (112, 78, 150)


def load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    name = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    path = Path("/usr/share/fonts/truetype/dejavu") / name
    if path.exists():
        return ImageFont.truetype(str(path), size=size)
    return ImageFont.load_default()


def new_canvas(width: int, height: int, title: str, subtitle: str | None = None):
    canvas = Image.new("RGB", (width, height), OUT_BG)
    draw = ImageDraw.Draw(canvas)
    draw.text((56, 30), title, fill=INK, font=load_font(22, bold=True))
    if subtitle:
        draw.text((56, 60), subtitle, fill=MUTED, font=load_font(12))
    return canvas, draw


def footer(draw: ImageDraw.ImageDraw, width: int, height: int, text: str) -> None:
    draw.text((56, height - 38), text, fill=MUTED, font=load_font(10))


def value_labels(draw, bars, fmt="{:.2f}", color=INK) -> None:
    for x, y, label in bars:
        draw.text((x, y), fmt.format(label), fill=color, font=load_font(11, bold=True), anchor="ms")


def render_capacity() -> Path:
    source = ROOT / "theories/01-surebet-capacity/results/sample/capacity_output.json"
    data = json.loads(source.read_text(encoding="utf-8"))
    rows = data["results"]
    width, height = 1100, 620
    canvas, draw = new_canvas(
        width,
        height,
        "Surebet capacity replay: ROI falls as size grows",
        "Two-venue complementary book, sample snapshot, 0 bps fees",
    )
    left, right, top, bottom = 90, width - 60, 120, height - 90
    plot_w, plot_h = right - left, bottom - top
    max_roi = max(r["profitAnalysis"]["roi"] for r in rows) * 1.25
    y_max = math.ceil(max_roi / 2) * 2

    for tick in range(0, y_max + 1, 2):
        y = bottom - (tick / y_max) * plot_h
        draw.line([(left, y), (right, y)], fill=GRID)
        draw.text((left - 14, y), f"{tick}%", fill=MUTED, font=load_font(11), anchor="rm")
    draw.line([(left, top), (left, bottom)], fill=(170, 170, 170))
    draw.line([(left, bottom), (right, bottom)], fill=(170, 170, 170))

    slot = plot_w / len(rows)
    bar_w = min(110, slot * 0.55)
    labels = []
    for index, row in enumerate(rows):
        q = row["marketA"]["quantityRange"]
        roi = row["profitAnalysis"]["roi"]
        x_center = left + slot * (index + 0.5)
        bar_h = (roi / y_max) * plot_h
        x0, x1 = x_center - bar_w / 2, x_center + bar_w / 2
        y0 = bottom - bar_h
        draw.rounded_rectangle([x0, y0, x1, bottom], radius=4, fill=GREEN)
        label = f"{q['min']}-{q['max']} shares"
        draw.text((x_center, bottom + 14), label, fill=INK, font=load_font(11), anchor="ma")
        draw.text(
            (x_center, bottom + 32),
            f"cost ${row['profitAnalysis']['maxTotalCostUSD']:.2f}",
            fill=MUTED,
            font=load_font(10),
            anchor="ma",
        )
        labels.append((x_center, y0 - 8, roi))
    value_labels(draw, labels, "{:.2f}%")
    draw.text((left, top - 26), "ROI on maximum size in each book segment", fill=MUTED, font=load_font(11))
    draw.text((left - 46, (top + bottom) / 2), "ROI", fill=MUTED, font=load_font(11), anchor="mm")
    footer(
        draw,
        width,
        height,
        "Source: results/sample/capacity_output.json. Settlement, capital lockup, withdrawal and resolution risk are excluded.",
    )
    out = ROOT / "theories/01-surebet-capacity/results/capacity_roi.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out, format="PNG", optimize=True)
    print(f"wrote {out}")
    return out


def render_clusters() -> Path:
    source = ROOT / "theories/05-bloomberg-from-crypto/results/cluster_report.json"
    data = json.loads(source.read_text(encoding="utf-8"))
    clusters = data["clusters"]
    times = []
    for cluster in clusters:
        times.append(datetime.fromisoformat(cluster["firstSeen"].replace("Z", "+00:00")))
        times.append(datetime.fromisoformat(cluster["lastSeen"].replace("Z", "+00:00")))
    start, end = min(times), max(times)
    span = max((end - start).total_seconds() / 60, 1)

    width, height = 1150, 560
    canvas, draw = new_canvas(
        width,
        height,
        "Synthetic launch clusters: four bursts inside a 20-minute window",
        f"{data['clusterCount']} clusters from {data['totalTimestamps']} timestamps and {data['itemCount']} items",
    )
    left, right, top = 340, width - 70, 125
    row_h = 76
    plot_w = right - left

    def x_of(moment: datetime) -> float:
        minutes = (moment - start).total_seconds() / 60
        return left + (minutes / span) * plot_w

    tick = start.replace(second=0, microsecond=0)
    while tick <= end + (end - start) * 0.05:
        x = x_of(tick)
        draw.line([(x, top - 12), (x, top + row_h * len(clusters))], fill=GRID)
        draw.text((x, top + row_h * len(clusters) + 12), tick.strftime("%H:%M"), fill=MUTED, font=load_font(10), anchor="ma")
        tick = tick.replace(minute=tick.minute + 1) if tick.minute < 59 else tick.replace(hour=tick.hour + 1, minute=0)

    for index, cluster in enumerate(clusters):
        y = top + index * row_h + 12
        first = datetime.fromisoformat(cluster["firstSeen"].replace("Z", "+00:00"))
        last = datetime.fromisoformat(cluster["lastSeen"].replace("Z", "+00:00"))
        x0 = x_of(first)
        x1 = max(x_of(last), x0 + 8)
        keywords = " / ".join(cluster["keywords"])
        draw.text((left - 18, y + 10), keywords, fill=INK, font=load_font(12, bold=True), anchor="rm")
        draw.rounded_rectangle([x0, y, x1, y + 34], radius=6, fill=ORANGE)
        detail = f"{cluster['timestamps']} timestamps · {cluster['spanMinutes']} min"
        draw.text((x0 + 8, y + 8), detail, fill=(255, 255, 255), font=load_font(10))

    footer(
        draw,
        width,
        height,
        "Source: results/cluster_report.json. Synthetic sample; timestamps are UTC and this is not a live-news result.",
    )
    out = ROOT / "theories/05-bloomberg-from-crypto/results/cluster_timeline.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out, format="PNG", optimize=True)
    print(f"wrote {out}")
    return out


def render_lift() -> Path:
    source = ROOT / "theories/15-launch-filters/results/filter_analysis_report.json"
    data = json.loads(source.read_text(encoding="utf-8"))
    overview = data["data_overview"]
    filt = data["filter"]
    width, height = 1150, 620
    canvas, draw = new_canvas(
        width,
        height,
        "Deduplication removes the apparent launch-filter edge",
        f"Row-level pools vs one row per token; {overview['unique_discovery_tokens']:,} unique tokens; lift about +0.1 pp",
    )

    # Left panel: win rates.
    left_box = (90, 140, 560, height - 100)
    draw.text((left_box[0], 110), "Win rate (%)", fill=INK, font=load_font(13, bold=True))
    rate_rows = [
        ("Row-level\nbaseline", overview["row_level_success_rate"], MUTED),
        ("Token-level\nbaseline", overview["token_level_success_rate"], BLUE),
        ("Token-level\nfilter", filt["primary_pool"]["winrate"], GREEN),
    ]
    left, top, right, bottom = left_box
    y_min, y_max = 55.0, 57.5
    plot_h = bottom - top
    for tick in (55.5, 56.0, 56.5, 57.0):
        y = bottom - ((tick - y_min) / (y_max - y_min)) * plot_h
        draw.line([(left, y), (right, y)], fill=GRID)
        draw.text((left - 12, y), f"{tick:.1f}", fill=MUTED, font=load_font(10), anchor="rm")
    slot = (right - left) / len(rate_rows)
    bar_w = 78
    for index, (label, value, color) in enumerate(rate_rows):
        x_center = left + slot * (index + 0.5)
        bar_h = ((value - y_min) / (y_max - y_min)) * plot_h
        y0 = bottom - bar_h
        draw.rectangle([x_center - bar_w / 2, y0, x_center + bar_w / 2, bottom], fill=color)
        draw.text((x_center, y0 - 8), f"{value:.2f}", fill=INK, font=load_font(11, bold=True), anchor="ms")
        draw.multiline_text(
            (x_center, bottom + 12), label, fill=INK, font=load_font(10), anchor="ma", align="center", spacing=2
        )
    # Right panel: lift in percentage points.
    right_box = (660, 140, width - 70, height - 100)
    draw.text((right_box[0], 110), "Filter lift (percentage points)", fill=INK, font=load_font(13, bold=True))
    lift_rows = [
        ("Primary\nfilter", filt["primary_pool"]["lift_pp"], GREEN),
        ("Early 70%\nholdout", filt["temporal_holdout"]["early_70pct"]["lift_pp"], BLUE),
        ("Late 30%\nholdout", filt["temporal_holdout"]["late_30pct"]["lift_pp"], ORANGE),
    ]
    left, top, right, bottom = right_box
    y_max = 0.20
    plot_h = bottom - top
    for tick in (0.0, 0.05, 0.10, 0.15, 0.20):
        y = bottom - (tick / y_max) * plot_h
        draw.line([(left, y), (right, y)], fill=GRID)
        draw.text((left - 12, y), f"+{tick:.2f}", fill=MUTED, font=load_font(10), anchor="rm")
    slot = (right - left) / len(lift_rows)
    bar_w = 62
    for index, (label, value, color) in enumerate(lift_rows):
        x_center = left + slot * (index + 0.5)
        bar_h = (value / y_max) * plot_h
        y0 = bottom - bar_h
        draw.rectangle([x_center - bar_w / 2, y0, x_center + bar_w / 2, bottom], fill=color)
        draw.text((x_center, y0 - 8), f"+{value:.2f}", fill=INK, font=load_font(11, bold=True), anchor="ms")
        draw.multiline_text(
            (x_center, bottom + 12), label, fill=INK, font=load_font(10), anchor="ma", align="center", spacing=2
        )

    footer(
        draw,
        width,
        height,
        "Source: results/filter_analysis_report.json. Fees, slippage, liquidity and multiple testing are not modeled.",
    )
    out = ROOT / "theories/15-launch-filters/results/filter_lift.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out, format="PNG", optimize=True)
    print(f"wrote {out}")
    return out


def render_leverage() -> Path:
    source = ROOT / "theories/08-leaderboard-positioning/data/sample/coin-leverage-history.json"
    rows = json.loads(source.read_text(encoding="utf-8"))
    by_day = defaultdict(lambda: {"BTC": [], "ETH": []})
    for row in rows:
        day = datetime.fromtimestamp(row["ts"] / 1000, tz=timezone.utc).date()
        for symbol in ("BTC", "ETH"):
            value = row[symbol]["levDelta"]
            if value is not None:
                by_day[day][symbol].append(value)
    days = sorted(by_day)
    series = {
        symbol: [statistics.mean(by_day[day][symbol]) if by_day[day][symbol] else None for day in days]
        for symbol in ("BTC", "ETH")
    }
    values = [v for symbol in series for v in series[symbol] if v is not None]
    y_min = math.floor(min(values) / 20) * 20
    y_max = math.ceil(max(values) / 20) * 20

    width, height = 1150, 620
    canvas, draw = new_canvas(
        width,
        height,
        "Synthetic leaderboard panel: average leverage imbalance",
        "Daily mean of long average leverage minus short average leverage",
    )
    left, right, top, bottom = 90, width - 60, 120, height - 100
    plot_w, plot_h = right - left, bottom - top

    for tick in range(y_min, y_max + 1, 20):
        y = bottom - ((tick - y_min) / (y_max - y_min)) * plot_h
        draw.line([(left, y), (right, y)], fill=GRID)
        draw.text((left - 14, y), f"{tick:+d}", fill=MUTED, font=load_font(10), anchor="rm")
    zero_y = bottom - ((0 - y_min) / (y_max - y_min)) * plot_h
    draw.line([(left, zero_y), (right, zero_y)], fill=(150, 150, 150), width=2)

    def x_of(index: int) -> float:
        return left + (index / max(len(days) - 1, 1)) * plot_w

    for symbol, color in (("BTC", ORANGE), ("ETH", PURPLE)):
        points = []
        for index, value in enumerate(series[symbol]):
            if value is None:
                continue
            points.append((x_of(index), bottom - ((value - y_min) / (y_max - y_min)) * plot_h))
        if len(points) > 1:
            draw.line(points, fill=color, width=3)
        for x, y in points[:: max(1, len(points) // 40)]:
            draw.ellipse([x - 2, y - 2, x + 2, y + 2], fill=color)

    legend_x = right - 150
    for offset, (symbol, color) in enumerate((("BTC", ORANGE), ("ETH", PURPLE))):
        y = top + 10 + offset * 22
        draw.line([(legend_x, y + 6), (legend_x + 24, y + 6)], fill=color, width=3)
        draw.text((legend_x + 32, y), symbol, fill=INK, font=load_font(11))

    for index in range(0, len(days), max(1, len(days) // 6)):
        draw.text((x_of(index), bottom + 12), days[index].isoformat(), fill=MUTED, font=load_font(10), anchor="ma")
    draw.text((left, top - 28), "Leverage points (long average - short average)", fill=MUTED, font=load_font(11))

    footer(
        draw,
        width,
        height,
        "Source: data/sample/coin-leverage-history.json. Synthetic EXAMPLE_UID panel; spikes can reflect thin or zero short samples.",
    )
    out = ROOT / "theories/08-leaderboard-positioning/results/leaderboard_leverage.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out, format="PNG", optimize=True)
    print(f"wrote {out}")
    return out


def render_attention() -> Path:
    source = ROOT / "theories/16-attention-index/data/sample/google-news.json"
    raw = json.loads(source.read_text(encoding="utf-8"))
    rows = []
    for row in raw:
        try:
            stamp = datetime.fromisoformat(row["timestamp"].replace("Z", "+00:00"))
            rows.append((stamp, float(row["totalHits"])))
        except (KeyError, TypeError, ValueError):
            continue
    rows.sort()
    values = [value for _, value in rows]
    median = statistics.median(values)

    width, height = 1200, 650
    canvas, draw = new_canvas(
        width,
        height,
        "Google News bitcoin count: a noisy, gappy attention proxy",
        f"{len(rows)} usable daily observations, {rows[0][0].date()} to {rows[-1][0].date()}; log scale",
    )
    left, right, top, bottom = 100, width - 70, 120, height - 100
    plot_w, plot_h = right - left, bottom - top
    y_max = 10500
    log_max = math.log10(1 + y_max)

    for tick in (0, 10, 100, 1000, 10000):
        y = bottom - (math.log10(1 + tick) / log_max) * plot_h
        draw.line([(left, y), (right, y)], fill=GRID)
        draw.text((left - 14, y), f"{tick:,}", fill=MUTED, font=load_font(10), anchor="rm")
    draw.line([(left, top), (left, bottom)], fill=(170, 170, 170))
    draw.line([(left, bottom), (right, bottom)], fill=(170, 170, 170))

    start, end = rows[0][0], rows[-1][0]
    span = max((end - start).total_seconds(), 1)

    def x_of(stamp: datetime) -> float:
        return left + ((stamp - start).total_seconds() / span) * plot_w

    def y_of(value: float) -> float:
        return bottom - (math.log10(1 + max(value, 0)) / log_max) * plot_h

    # Break the line across gaps longer than two days.
    segment = []
    for stamp, value in rows:
        if segment and (stamp - segment[-1][0]).total_seconds() > 2 * 86400:
            if len(segment) > 1:
                draw.line([(x_of(t), y_of(v)) for t, v in segment], fill=BLUE, width=2)
            segment = []
        segment.append((stamp, value))
    if len(segment) > 1:
        draw.line([(x_of(t), y_of(v)) for t, v in segment], fill=BLUE, width=2)

    median_y = y_of(median)
    draw.line([(left, median_y), (right, median_y)], fill=(140, 140, 140), width=1)
    median_label = f"median {median:,.0f}"
    label_box = draw.textbbox((0, 0), median_label, font=load_font(10))
    label_w = label_box[2] - label_box[0]
    draw.rectangle([right - label_w - 12, median_y - 18, right - 4, median_y - 2], fill=OUT_BG)
    draw.text((right - 8, median_y - 8), median_label, fill=MUTED, font=load_font(10), anchor="rs")

    peak = max(rows, key=lambda item: item[1])
    px, py = x_of(peak[0]), y_of(peak[1])
    draw.ellipse([px - 4, py - 4, px + 4, py + 4], fill=RED)
    draw.text((px - 10, py - 12), f"{peak[1]:,.0f} (cap?)", fill=RED, font=load_font(10), anchor="rs")

    for index in range(0, 7):
        stamp = start + (end - start) * (index / 6)
        draw.text((x_of(stamp), bottom + 12), stamp.date().isoformat(), fill=MUTED, font=load_font(10), anchor="ma")

    footer(
        draw,
        width,
        height,
        "Source: data/sample/google-news.json. Log scale; not joined to prices or flow; 78 days missing; 10,000 looks capped.",
    )
    out = ROOT / "theories/16-attention-index/results/google-news-attention.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out, format="PNG", optimize=True)
    print(f"wrote {out}")
    return out


def render_weather() -> Path:
    source = ROOT / "theories/18-weather-mood/results/weather_effects.json"
    data = json.loads(source.read_text(encoding="utf-8"))
    primary = data["primary"]
    cross = data["cross_market"]
    placebo = data["placebo"]

    left_rows = [
        ("SPY · winter", primary["spy_winter_morning_heat"]),
        ("QQQ · winter", primary["qqq_winter_morning_heat"]),
        ("IWM · winter", primary["iwm_winter_morning_heat"]),
        ("SPY · summer", primary["spy_summer_morning_heat"]),
        ("SPY · all year", primary["spy_all_year_morning_heat"]),
    ]
    right_rows = [
        ("London · winter warm", cross["FTSE"]["winter_morning_heat"]),
        ("Frankfurt · winter warm", cross["DAX"]["winter_morning_heat"]),
        ("Tokyo · winter warm", cross["NIKKEI"]["winter_morning_heat"]),
        ("Denver · winter warm", placebo["denver_morning_heat"]),
        ("London · winter cold", cross["FTSE"]["winter_morning_cold"]),
    ]

    width, height = 1320, 640
    canvas, draw = new_canvas(
        width,
        height,
        "Unseasonable winter warmth is the one weather bucket that moved the market",
        "SPY open-to-close return, 2000–2026; adjusted difference in basis points with 95% HAC intervals",
    )

    def panel(rows, box, x_min, x_max, ticks, title, note):
        left, top, right, bottom = box
        plot_w = right - left
        value_x = right + 14
        draw.text((left, top - 34), title, fill=INK, font=load_font(13, bold=True))
        draw.text((left, top - 14), note, fill=MUTED, font=load_font(10))

        def x_of(value):
            return left + (value - x_min) / (x_max - x_min) * plot_w

        for tick in ticks:
            x = x_of(tick)
            draw.line([(x, top), (x, bottom)], fill=GRID)
            draw.text((x, bottom + 10), f"{tick:+d}" if tick else "0", fill=MUTED, font=load_font(10), anchor="ma")
        zero = x_of(0)
        draw.line([(zero, top - 4), (zero, bottom)], fill=(135, 135, 135), width=1)

        slot = (bottom - top) / len(rows)
        for index, (label, result) in enumerate(rows):
            if not result:
                continue
            center = top + slot * (index + 0.5)
            low = result["ci_low_bps"]
            high = result["ci_high_bps"]
            effect = result["effect_bps"]
            significant = low > 0 or high < 0
            color = RED if (significant and effect < 0) else GREEN if significant else MUTED
            draw.text((left - 14, center), label, fill=INK, font=load_font(11), anchor="rm")
            y0, y1 = center - 12, center + 12
            x0, x1 = x_of(min(0, effect)), x_of(max(0, effect))
            draw.rectangle([min(x0, x1), y0, max(x0, x1), y1], fill=color)
            draw.line([(x_of(low), center), (x_of(high), center)], fill=color, width=2)
            for cap in (low, high):
                draw.line([(x_of(cap), y0 + 4), (x_of(cap), y1 - 4)], fill=color, width=2)
            draw.text((value_x, center), f"{effect:+.1f} bps", fill=color, font=load_font(10), anchor="lm")

    panel(
        left_rows,
        (250, 155, 590, 520),
        -70,
        20,
        (-70, -50, -30, -10, 0),
        "New York: winter warmth, not summer heat",
        "Warm morning = 10:00–11:00 apparent temperature in the top 5% of its month",
    )
    panel(
        right_rows,
        (880, 155, 1150, 520),
        -45,
        60,
        (-40, -20, 0, 20, 40, 60),
        "The same rule in other cities",
        "Local cash-session weather; Denver is a clock-time placebo",
    )

    legend_y = 560
    draw.rectangle([250, legend_y, 262, legend_y + 12], fill=RED)
    draw.text((270, legend_y + 6), "negative, interval excludes zero", fill=MUTED, font=load_font(10), anchor="lm")
    draw.rectangle([510, legend_y, 522, legend_y + 12], fill=GREEN)
    draw.text((530, legend_y + 6), "positive, interval excludes zero", fill=MUTED, font=load_font(10), anchor="lm")
    draw.rectangle([770, legend_y, 782, legend_y + 12], fill=MUTED)
    draw.text((790, legend_y + 6), "interval includes zero", fill=MUTED, font=load_font(10), anchor="lm")

    footer(
        draw,
        width,
        height,
        "Source: results/weather_effects.json. Daily bars; day-of-year fixed effects and HAC(10). The signal is read at 11:00, so the open-to-close estimate is not a tradeable return.",
    )
    out = ROOT / "theories/18-weather-mood/results/weather_winter_effect.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out, format="PNG", optimize=True)
    print(f"wrote {out}")
    return out


def main() -> int:
    render_capacity()
    render_clusters()
    render_lift()
    render_leverage()
    render_attention()
    render_weather()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
