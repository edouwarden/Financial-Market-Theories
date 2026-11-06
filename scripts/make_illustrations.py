#!/usr/bin/env python3
"""Render the small inline theory illustrations with Pillow.

These are explanatory diagrams, not data. They are generated offline so the
README can show a compact visual without an external image service:

    python3 scripts/make_illustrations.py

Each function writes one PNG under ``assets/illustrations/``. The README embeds
them with an explicit width so they stay small next to the text.
"""

from __future__ import annotations

import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets/illustrations"

BG = (250, 250, 247)
CARD = (255, 255, 255)
INK = (30, 33, 38)
MUTED = (105, 112, 122)
GRID = (224, 226, 222)
GREEN = (39, 128, 82)
GREEN_FILL = (232, 244, 236)
RED = (176, 58, 58)
RED_FILL = (250, 235, 235)
BLUE = (53, 103, 172)
BLUE_FILL = (232, 240, 250)
ORANGE = (194, 120, 42)
ORANGE_FILL = (252, 240, 228)
PURPLE = (112, 78, 150)


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    name = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    path = Path("/usr/share/fonts/truetype/dejavu") / name
    if path.exists():
        return ImageFont.truetype(str(path), size=size)
    return ImageFont.load_default()


def canvas(width: int, height: int, title: str, subtitle: str | None = None):
    image = Image.new("RGB", (width, height), BG)
    draw = ImageDraw.Draw(image)
    draw.text((44, 26), title, fill=INK, font=font(24, bold=True))
    if subtitle:
        draw.text((44, 60), subtitle, fill=MUTED, font=font(14))
    return image, draw


def footer(draw: ImageDraw.ImageDraw, width: int, height: int, text: str) -> None:
    draw.text((44, height - 34), text, fill=MUTED, font=font(13))


def dashed(draw, start, end, fill, width=2, dash=9, gap=7) -> None:
    x0, y0 = start
    x1, y1 = end
    length = ((x1 - x0) ** 2 + (y1 - y0) ** 2) ** 0.5
    if length == 0:
        return
    ux, uy = (x1 - x0) / length, (y1 - y0) / length
    pos = 0.0
    while pos < length:
        a = (x0 + ux * pos, y0 + uy * pos)
        pos = min(pos + dash, length)
        b = (x0 + ux * pos, y0 + uy * pos)
        draw.line([a, b], fill=fill, width=width)
        pos += gap


def make_ohlc(start: float, drift: float, volatility: float, count: int, seed: int):
    rng = random.Random(seed)
    candles = []
    price = start
    for _ in range(count):
        open_ = price
        close = open_ * (1 + drift + rng.uniform(-volatility, volatility))
        high = max(open_, close) * (1 + rng.uniform(0.001, volatility * 0.8))
        low = min(open_, close) * (1 - rng.uniform(0.001, volatility * 0.8))
        candles.append((open_, high, low, close))
        price = close
    return candles


def make_oi(start: float, end: float, count: int, seed: int, noise: float = 2.0):
    rng = random.Random(seed)
    return [
        start + (end - start) * (index / (count - 1)) + rng.uniform(-noise, noise)
        for index in range(count)
    ]


def draw_price_panel(draw, box, candles, oi, oi_bounds, title, note, accent, fill) -> None:
    x0, y0, x1, y1 = box
    draw.rounded_rectangle([x0, y0, x1, y1], radius=10, fill=fill, outline=accent, width=2)
    draw.text((x0 + 14, y0 + 12), title, fill=accent, font=font(17, bold=True))
    draw.text((x0 + 14, y0 + 36), note, fill=MUTED, font=font(13))

    left, top, right, bottom = x0 + 16, y0 + 64, x1 - 16, y1 - 30
    plot_w, plot_h = right - left, bottom - top
    price_low = min(candle[2] for candle in candles)
    price_high = max(candle[1] for candle in candles)
    price_pad = (price_high - price_low) * 0.08
    price_low -= price_pad
    price_high += price_pad
    oi_low, oi_high = oi_bounds

    def price_y(value: float) -> float:
        return bottom - ((value - price_low) / (price_high - price_low)) * plot_h

    def oi_y(value: float) -> float:
        return bottom - ((value - oi_low) / (oi_high - oi_low)) * plot_h

    for step in (0.0, 0.5, 1.0):
        y = top + step * plot_h
        draw.line([(left, y), (right, y)], fill=GRID)

    slot = plot_w / len(candles)
    body = max(slot * 0.52, 3)
    centers = []
    for index, (open_, high, low, close) in enumerate(candles):
        x = left + slot * (index + 0.5)
        centers.append(x)
        color = GREEN if close >= open_ else RED
        draw.line([(x, price_y(high)), (x, price_y(low))], fill=color, width=1)
        y_top = min(price_y(open_), price_y(close))
        y_bottom = max(price_y(open_), price_y(close))
        draw.rectangle([x - body / 2, y_top, x + body / 2, max(y_bottom, y_top + 2)], fill=color)

    points = [(centers[index], oi_y(value)) for index, value in enumerate(oi)]
    draw.line(points, fill=PURPLE, width=2, joint="curve")
    draw.text((points[-1][0] + 5, points[-1][1] - 7), "OI", fill=PURPLE, font=font(11, bold=True))
    draw.text((left, y1 - 18), "candles = price  ·  line = OI", fill=MUTED, font=font(10))


def render_price_oi() -> Path:
    width, height = 940, 720
    image, draw = canvas(
        width,
        height,
        "Price moves vs open interest growth",
        "Same price path, different OI response: crowded versus healthy",
    )

    up = make_ohlc(100.0, 0.010, 0.008, 22, seed=11)
    down = make_ohlc(100.0, -0.010, 0.008, 22, seed=11)
    up_oi_heavy = make_oi(100.0, 190.0, len(up), seed=21, noise=2.5)
    up_oi_light = make_oi(100.0, 94.0, len(up), seed=22, noise=2.0)
    down_oi_heavy = make_oi(100.0, 190.0, len(down), seed=23, noise=2.5)
    down_oi_light = make_oi(100.0, 94.0, len(down), seed=24, noise=2.0)

    all_oi = up_oi_heavy + up_oi_light + down_oi_heavy + down_oi_light
    oi_bounds = (min(all_oi) - 8, max(all_oi) + 8)

    panels = [
        ((48, 112, 468, 360), up, up_oi_heavy, "Price ↑ · OI ↑↑", "Unhealthy: crowded longs", RED, RED_FILL),
        ((492, 112, 912, 360), up, up_oi_light, "Price ↑ · OI lags", "Healthy: spot demand", GREEN, GREEN_FILL),
        ((48, 388, 468, 636), down, down_oi_heavy, "Price ↓ · OI ↑↑", "Unhealthy: crowded shorts", RED, RED_FILL),
        ((492, 388, 912, 636), down, down_oi_light, "Price ↓ · OI lags", "Healthy: deleveraging", GREEN, GREEN_FILL),
    ]
    for box, candles, oi, title, note, accent, fill in panels:
        draw_price_panel(draw, box, candles, oi, oi_bounds, title, note, accent, fill)

    footer(
        draw,
        width,
        height,
        "When OI grows faster than price, the move is funded by new leverage. When OI lags, it is closer to spot.",
    )
    out = OUT / "price-oi-health.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    image.save(out, format="PNG", optimize=True)
    print(f"wrote {out}")
    return out


def render_liquidation_levels() -> Path:
    width, height = 760, 450
    image, draw = canvas(
        width,
        height,
        "Liquidation levels: pivots become magnets",
        "Each new open-interest addition sits at the pivot it entered from",
    )
    left, right = 90, 710
    levels = [
        (330, "early pivot", (170, 170, 170), 2),
        (255, "pivot + new OI", ORANGE, 3),
        (180, "latest pivot, most OI", RED, 4),
    ]
    for y, label, color, thickness in levels:
        dashed(draw, (left, y), (right, y), color, width=thickness)
        draw.text((right - 4, y - 20), label, fill=color, font=font(13, bold=True), anchor="ra")

    points = [(left + 20, 215), (190, 195), (250, 250), (320, 235), (390, 300), (455, 275), (520, 330), (590, 300), (650, 360), (700, 420)]
    draw.line(points, fill=INK, width=4, joint="curve")
    draw.ellipse([points[0][0] - 5, points[0][1] - 5, points[0][0] + 5, points[0][1] + 5], fill=INK)

    for x, y in ((250, 250), (455, 275), (590, 300)):
        draw.line([(x, y), (x, y - 26)], fill=RED, width=2)
        draw.polygon([(x - 5, y - 26), (x + 5, y - 26), (x, y - 34)], fill=RED)

    draw.text((104, 150), "stops and liquidations sit just beyond the pivot", fill=MUTED, font=font(13))
    footer(draw, width, height, "Fresh OI at a pivot marks where stops and liquidations cluster.")
    out = OUT / "liquidation-levels.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    image.save(out, format="PNG", optimize=True)
    print(f"wrote {out}")
    return out


def make_listing_candles(end_return: float, knee: float, count: int, seed: int, volatility: float = 0.022):
    """Candles for one listing path: flat until ``knee`` minutes, then move to ``end_return``."""
    rng = random.Random(seed)
    closes = []
    for index in range(count):
        minute = 60 * index / (count - 1)
        if minute <= knee:
            base = 100.0
        else:
            progress = (minute - knee) / (60 - knee)
            progress = progress ** 0.5
            base = 100.0 * (1 + end_return * progress)
        closes.append(base * (1 + rng.uniform(-volatility, volatility)))

    candles = []
    previous = 100.0
    for close in closes:
        open_ = previous + (close - previous) * 0.4
        high = max(open_, close) * (1 + rng.uniform(0.001, volatility * 0.7))
        low = min(open_, close) * (1 - rng.uniform(0.001, volatility * 0.7))
        candles.append((open_, high, low, close))
        previous = close
    return candles


def draw_listing_panel(draw, box, candles, title, note, accent, price_window) -> None:
    x0, y0, x1, y1 = box
    draw.rounded_rectangle([x0, y0, x1, y1], radius=10, fill=CARD, outline=GRID)
    draw.text((x0 + 13, y0 + 11), title, fill=INK, font=font(15, bold=True))
    draw.text((x0 + 13, y0 + 33), note, fill=accent, font=font(12))

    left, top, right, bottom = x0 + 14, y0 + 58, x1 - 14, y1 - 30
    low, high = price_window

    def price_y(value: float) -> float:
        return bottom - ((value - low) / (high - low)) * (bottom - top)

    # The dashed line is the first traded price; candles sit above or below it.
    dashed(draw, (left, price_y(100)), (right, price_y(100)), (185, 190, 196), width=1, dash=4, gap=4)

    slot = (right - left) / len(candles)
    body = max(slot * 0.62, 3.0)
    for index, (open_, high_, low_, close) in enumerate(candles):
        x = left + slot * (index + 0.5)
        color = GREEN if close >= open_ else RED
        draw.line([(x, price_y(high_)), (x, price_y(low_))], fill=color, width=1)
        y_top = price_y(max(open_, close))
        y_bottom = price_y(min(open_, close))
        draw.rectangle([x - body / 2, y_top, x + body / 2, max(y_bottom, y_top + 1.5)], fill=color)

    for minute, label in ((0, "0m"), (30, "30m"), (60, "60m")):
        px = left + (minute / 60) * (right - left)
        draw.text((px, bottom + 6), label, fill=MUTED, font=font(10), anchor="ma")


def render_listing_paths() -> Path:
    width, height = 1120, 400
    image, draw = canvas(
        width,
        height,
        "First hour after listing: the drop is not one shape",
        "Candles across the first hour. Depth and timing vary; most falls land between 20% and 40%.",
    )

    panels = [
        ("−20%", "after 5–10 min", make_listing_candles(-0.20, 8, 15, seed=31), RED),
        ("−20%", "from the open", make_listing_candles(-0.20, 0, 15, seed=32), RED),
        ("−30%", "from the open", make_listing_candles(-0.30, 1, 15, seed=33), RED),
        ("−40%", "deep and fast, rare", make_listing_candles(-0.40, 0, 15, seed=34), RED),
        ("Up", "rare, about 10% of listings", make_listing_candles(0.20, 0, 15, seed=35), GREEN),
    ]

    gap = 12
    panel_w = (width - 88 - gap * (len(panels) - 1)) / len(panels)
    top, bottom = 104, 350
    # One shared price scale so the depth of each move is comparable.
    price_window = (54.0, 126.0)

    for index, (title, note, candles, accent) in enumerate(panels):
        x0 = 44 + index * (panel_w + gap)
        draw_listing_panel(
            draw,
            (x0, top, x0 + panel_w, bottom),
            candles,
            title,
            note,
            accent,
            price_window,
        )

    footer(
        draw,
        width,
        height,
        "Most listings fall 20–40%; about 10% fall more slowly, or go up from the open.",
    )
    out = OUT / "listing-first-hour-paths.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    image.save(out, format="PNG", optimize=True)
    print(f"wrote {out}")
    return out


def render_orderbook_walls() -> Path:
    width, height = 760, 470
    image, draw = canvas(
        width,
        height,
        "What the wall detector sees",
        "Visible size around the mid price, not hidden intent",
    )
    mid_y, mid_x = 235, 380
    levels = [
        (110, 90, "ask wall", RED, True),
        (150, 42, "", RED, False),
        (190, 26, "", RED, False),
        (280, 30, "", GREEN, False),
        (320, 58, "", GREEN, False),
        (360, 96, "bid wall", GREEN, True),
    ]
    draw.line([(80, mid_y), (680, mid_y)], fill=(160, 165, 170), width=2)
    draw.text((688, mid_y - 8), "mid", fill=MUTED, font=font(13), anchor="lm")
    for y, size, label, color, wall in levels:
        bar = size * 2.2
        x0 = mid_x if y < mid_y else mid_x - bar
        x1 = mid_x + bar if y < mid_y else mid_x
        draw.rounded_rectangle([x0, y - 11, x1, y + 11], radius=4, fill=color)
        if wall:
            draw.rounded_rectangle([x0, y - 11, x1, y + 11], radius=4, outline=INK, width=2)
        side = "ask" if y < mid_y else "bid"
        draw.text((80, y - 8), f"{side} {size}", fill=MUTED, font=font(12), anchor="lm")
        if label:
            label_x = x1 + 10 if y < mid_y else mid_x + 12
            draw.text((label_x, y - 8), label, fill=color, font=font(12, bold=True), anchor="lm")
    footer(draw, width, height, "Large visible size is context before placing an order.")
    out = OUT / "orderbook-walls.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    image.save(out, format="PNG", optimize=True)
    print(f"wrote {out}")
    return out


def render_attention_funnel() -> Path:
    width, height = 760, 430
    image, draw = canvas(
        width,
        height,
        "One attention index, four inputs",
        "Slow adoption data and fast search data, read together",
    )
    inputs = [
        ("Google News", "news volume", BLUE),
        ("Google Trends", "search interest", GREEN),
        ("TikTok", "short-video attention", PURPLE),
        ("Amazon sales", "hardware, books", ORANGE),
    ]
    box_w, box_h, gap = 156, 66, 14
    start_x = (width - (4 * box_w + 3 * gap)) / 2
    for index, (name, note, color) in enumerate(inputs):
        x0 = start_x + index * (box_w + gap)
        draw.rounded_rectangle([x0, 112, x0 + box_w, 112 + box_h], radius=8, fill=CARD, outline=color, width=2)
        draw.text((x0 + box_w / 2, 130), name, fill=INK, font=font(14, bold=True), anchor="ma")
        draw.text((x0 + box_w / 2, 152), note, fill=MUTED, font=font(11), anchor="ma")
        draw.line([(x0 + box_w / 2, 178), (x0 + box_w / 2, 214)], fill=(170, 175, 180), width=2)

    draw.rounded_rectangle([150, 218, 610, 290], radius=16, fill=(235, 239, 246), outline=BLUE, width=2)
    draw.text((380, 238), "Composite attention index", fill=INK, font=font(19, bold=True), anchor="ma")
    draw.text((380, 264), "news · search · social · product sales", fill=MUTED, font=font(12), anchor="ma")
    draw.line([(380, 294), (380, 330)], fill=(170, 175, 180), width=3)
    draw.polygon([(374, 330), (386, 330), (380, 340)], fill=(170, 175, 180))
    draw.rounded_rectangle([240, 344, 520, 394], radius=12, fill=CARD, outline=GREEN, width=2)
    draw.text((380, 360), "Retail flow and price", fill=GREEN, font=font(17, bold=True), anchor="ma")
    draw.text((380, 380), "confirmation, not a standalone trade", fill=MUTED, font=font(11), anchor="ma")
    footer(draw, width, height, "The Amazon leg is slower; the news and search legs are faster.")
    out = OUT / "attention-funnel.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    image.save(out, format="PNG", optimize=True)
    print(f"wrote {out}")
    return out


def main() -> int:
    render_price_oi()
    render_liquidation_levels()
    render_listing_paths()
    render_orderbook_walls()
    render_attention_funnel()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
