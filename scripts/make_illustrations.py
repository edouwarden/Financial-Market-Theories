#!/usr/bin/env python3
"""Render the small inline theory illustrations with Pillow.

These are explanatory diagrams, not data. They are generated offline so the
README can show a compact visual without an external image service:

    python3 scripts/make_illustrations.py

Each function writes one PNG under ``assets/illustrations/``. The README embeds
them with an explicit width so they stay small next to the text.
"""

from __future__ import annotations

import math
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


def blend(first, second, amount: float):
    amount = max(0.0, min(1.0, amount))
    return tuple(int(a + (b - a) * amount) for a, b in zip(first, second))


def render_cluster_latency() -> Path:
    width, height = 900, 620
    image, draw = canvas(
        width,
        height,
        "The sensor was early; the alert was late",
        "Venezuela helicopter episode, Paris time: detection and confirmation on two clocks",
    )
    left, right = 80, 860

    def lane(line_y, day_start, day_end, ticks, caption, caption_color, events):
        draw.text((left, line_y - 130), caption, fill=caption_color, font=font(12, bold=True))

        def tx(minute: int) -> float:
            return left + (minute - day_start) / (day_end - day_start) * (right - left)

        draw.line([(left, line_y), (right, line_y)], fill=(170, 175, 180), width=3)
        for minute in ticks:
            x = tx(minute)
            draw.line([(x, line_y - 7), (x, line_y + 7)], fill=(120, 125, 132), width=2)
            draw.text(
                (x, line_y + 14),
                f"{minute // 60:02d}:{minute % 60:02d}",
                fill=MUTED,
                font=font(11),
                anchor="ma",
            )
        for minute, time_label, title, note, color, above in events:
            x = tx(minute)
            if above:
                draw.line([(x, line_y), (x, line_y - 34)], fill=color, width=2)
                draw.text((x, line_y - 102), note, fill=MUTED, font=font(11), anchor="ma")
                draw.text((x, line_y - 78), title, fill=INK, font=font(13, bold=True), anchor="ma")
                draw.text((x, line_y - 54), time_label, fill=color, font=font(12, bold=True), anchor="ma")
            else:
                draw.line([(x, line_y), (x, line_y + 34)], fill=color, width=2)
                draw.text((x, line_y + 40), time_label, fill=color, font=font(12, bold=True), anchor="ma")
                draw.text((x, line_y + 60), title, fill=INK, font=font(13, bold=True), anchor="ma")
                draw.text((x, line_y + 82), note, fill=MUTED, font=font(11), anchor="ma")
            draw.ellipse([x - 6, line_y - 6, x + 6, line_y + 6], fill=color)

    lane(
        220,
        7 * 60 + 40,
        8 * 60 + 5,
        (7 * 60 + 45, 7 * 60 + 50, 8 * 60),
        "First sighting: 11 minutes from article to detection",
        GREEN,
        [
            (7 * 60 + 44, "07:44", "first articles", "helicopter over Venezuela", ORANGE, True),
            (7 * 60 + 55, "07:55", "first detection", "7 mentions in a 20-minute window", GREEN, False),
        ],
    )
    lane(
        480,
        10 * 60,
        10 * 60 + 50,
        (10 * 60 + 10, 10 * 60 + 20, 10 * 60 + 30, 10 * 60 + 50),
        "Actionable alert: 19 minutes after public confirmation",
        RED,
        [
            (10 * 60 + 21, "10:21", "Trump confirms", "public confirmation", ORANGE, True),
            (10 * 60 + 40, "10:40", "20-mention alert", "cluster arrives", RED, False),
        ],
    )

    footer(draw, width, height, "The sensor saw the story early; the 20-mention rule still delivered the alert after confirmation.")
    out = OUT / "cluster-latency.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    image.save(out, format="PNG", optimize=True)
    print(f"wrote {out}")
    return out


def render_implied_path() -> Path:
    width, height = 880, 460
    image, draw = canvas(
        width,
        height,
        "The implied path is already a price",
        "A repricing can lead other assets only if they adjust later",
    )
    left, top, right, bottom = 90, 120, 820, 380
    plot_h = bottom - top

    for step in (0.0, 0.25, 0.5, 0.75, 1.0):
        y = top + step * plot_h
        draw.line([(left, y), (right, y)], fill=GRID)
    draw.text((left - 14, top), "high", fill=MUTED, font=font(10), anchor="ra")
    draw.text((left - 14, bottom), "low", fill=MUTED, font=font(10), anchor="ra")

    event_x = left + 0.55 * (right - left)
    dashed(draw, (event_x, top), (event_x, bottom), ORANGE, width=2, dash=6, gap=5)
    draw.text((event_x + 10, top + 12), "repricing", fill=ORANGE, font=font(12, bold=True))
    draw.text((event_x + 10, top + 30), "FOMC · CPI · speech", fill=MUTED, font=font(10))

    step_points = [(left, 205), (event_x, 205), (event_x, 300), (right, 300)]
    draw.line(step_points, fill=BLUE, width=3, joint="curve")
    draw.text((right - 8, 284), "implied path", fill=BLUE, font=font(12, bold=True), anchor="ra")

    rng = random.Random(61)
    asset_points = []
    for index in range(41):
        x = left + index / 40 * (right - left)
        y = 252 + rng.uniform(-16, 16) + (4 if index > 30 else 0)
        asset_points.append((x, y))
    draw.line(asset_points, fill=ORANGE, width=3, joint="curve")
    draw.text((left + 8, asset_points[0][1] - 34), "other assets", fill=ORANGE, font=font(12, bold=True), anchor="la")

    draw.text((event_x + 12, 330), "does it follow?", fill=MUTED, font=font(12))
    footer(
        draw,
        width,
        height,
        "A change in the implied path updates a market price. The tradeable question is the second move.",
    )
    out = OUT / "implied-path-lead-lag.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    image.save(out, format="PNG", optimize=True)
    print(f"wrote {out}")
    return out


def render_oi_bands() -> Path:
    width, height = 880, 500
    image, draw = canvas(
        width,
        height,
        "Where positions were opened",
        "Open interest binned by price; opacity follows the size of the band",
    )
    left, top, right, bottom = 90, 120, 830, 430
    candles = make_ohlc(100.0, 0.0018, 0.014, 46, seed=91)
    price_low = min(candle[2] for candle in candles)
    price_high = max(candle[1] for candle in candles)
    pad = (price_high - price_low) * 0.06
    price_low -= pad
    price_high += pad

    def py(value: float) -> float:
        return bottom - (value - price_low) / (price_high - price_low) * (bottom - top)

    band_count = 10
    strengths = [2, 6, 3, 9, 5, 8, 4, 7, 3, 5]
    for index in range(band_count):
        low = price_low + (price_high - price_low) * index / band_count
        high = price_low + (price_high - price_low) * (index + 1) / band_count
        y0, y1 = py(high), py(low)
        positive = index % 3 != 1
        base = BLUE if positive else PURPLE
        strength = strengths[index] / 9
        draw.rectangle([left, y0, right, y1], fill=blend(BG, base, 0.08 + 0.28 * strength), outline=blend(BG, base, 0.28 + 0.3 * strength))

    draw.text((left + 10, top + 8), "OI added on up moves", fill=BLUE, font=font(11, bold=True))
    draw.text((left + 10, top + 26), "OI added on down moves", fill=PURPLE, font=font(11, bold=True))

    slot = (right - left) / len(candles)
    body = max(slot * 0.55, 3)
    for index, (open_, high, low, close) in enumerate(candles):
        x = left + slot * (index + 0.5)
        color = GREEN if close >= open_ else RED
        draw.line([(x, py(high)), (x, py(low))], fill=color, width=1)
        y_top = min(py(open_), py(close))
        y_bottom = max(py(open_), py(close))
        draw.rectangle([x - body / 2, y_top, x + body / 2, max(y_bottom, y_top + 2)], fill=color)

    last_price = candles[-1][3]
    dashed(draw, (left, py(last_price)), (right, py(last_price)), INK, width=2, dash=7, gap=5)
    draw.text((left + 8, py(last_price) - 18), "price now", fill=INK, font=font(11, bold=True), anchor="la")
    draw.text((left, bottom + 8), "price low", fill=MUTED, font=font(10))
    draw.text((left, top - 16), "price high", fill=MUTED, font=font(10))

    footer(
        draw,
        width,
        height,
        "A retest of a high-interest band can meet traders defending or adding to positions.",
    )
    out = OUT / "open-interest-bands.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    image.save(out, format="PNG", optimize=True)
    print(f"wrote {out}")
    return out


def render_supply_unlocks() -> Path:
    width, height = 880, 520
    image, draw = canvas(
        width,
        height,
        "An unlock is a schedule, not a sell order",
        "Circulating supply steps up; the price effect depends on who receives the tokens",
    )
    left, right = 90, 830
    supply_top, supply_bottom = 112, 280
    price_top, price_bottom = 320, 470
    volume_top = 442

    unlock_days = [45, 90, 135]
    unlock_sizes = [8, 12, 5]
    supply_low, supply_high = 96, 132
    price_low, price_high = 84, 112

    def sx(day: float) -> float:
        return left + day / 180 * (right - left)

    def supply_y(value: float) -> float:
        return supply_bottom - (value - supply_low) / (supply_high - supply_low) * (supply_bottom - supply_top)

    def price_y(value: float) -> float:
        return price_bottom - (value - price_low) / (price_high - price_low) * (price_bottom - price_top)

    draw.rounded_rectangle([left, supply_top, right, supply_bottom], radius=8, fill=CARD, outline=GRID)
    draw.rounded_rectangle([left, price_top, right, price_bottom], radius=8, fill=CARD, outline=GRID)
    draw.text((left + 12, supply_top + 10), "circulating supply", fill=BLUE, font=font(12, bold=True))
    draw.text((left + 12, price_top + 10), "price (indexed)", fill=INK, font=font(12, bold=True))

    supply = 100.0
    supply_points = [(left, supply_y(supply))]
    previous_x = left
    for day, size in zip(unlock_days, unlock_sizes):
        x = sx(day)
        supply_points.append((x, supply_y(supply)))
        supply += size
        supply_points.append((x, supply_y(supply)))
        previous_x = x
    supply_points.append((right, supply_y(supply)))
    draw.line(supply_points, fill=BLUE, width=3, joint="curve")

    for day, size in zip(unlock_days, unlock_sizes):
        x = sx(day)
        dashed(draw, (x, supply_top), (x, price_bottom), (196, 200, 206), width=1, dash=5, gap=5)
        draw.polygon([(x - 5, supply_top - 8), (x + 5, supply_top - 8), (x, supply_top - 16)], fill=ORANGE)
        draw.text((x, supply_top - 20), f"+{size}%", fill=ORANGE, font=font(10, bold=True), anchor="md")

    rng = random.Random(121)
    price_points = []
    value = 100.0
    for index in range(91):
        day = 2 * index
        value += rng.uniform(-1.1, 1.2)
        value = max(price_low + 2, min(price_high - 2, value))
        price_points.append((sx(day), price_y(value)))
    draw.line(price_points, fill=INK, width=2, joint="curve")

    for index in range(56):
        day = index * 180 / 55
        x = sx(day)
        height_bar = rng.uniform(4, 13)
        if min(abs(day - unlock) for unlock in unlock_days) < 9:
            height_bar *= 2.4
        draw.rectangle([x - 3, volume_top + (22 - height_bar), x + 3, volume_top + 22], fill=blend(BG, ORANGE, 0.45))

    draw.text((right - 10, supply_bottom - 20), "unlock cliffs", fill=MUTED, font=font(10), anchor="ra")
    footer(
        draw,
        width,
        height,
        "Recipient mix and vesting decide whether an unlock becomes sell pressure.",
    )
    out = OUT / "supply-unlocks.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    image.save(out, format="PNG", optimize=True)
    print(f"wrote {out}")
    return out


def draw_probability_panel(draw, box, values, labels, title, show_y: bool, show_50: bool = True) -> None:
    x0, y0, x1, y1 = box
    left, top, right, bottom = x0 + 44, y0 + 34, x1 - 8, y1 - 30
    low, high = 40.0, 60.0

    def py(value: float) -> float:
        return bottom - (value - low) / (high - low) * (bottom - top)

    draw.text((x0, y0), title, fill=INK, font=font(13, bold=True))
    for tick in (40, 45, 50, 55, 60):
        y = py(tick)
        draw.line([(left, y), (right, y)], fill=GRID)
        if show_y:
            draw.text((left - 8, y), str(tick), fill=MUTED, font=font(9), anchor="rm")
    dashed(draw, (left, py(50)), (right, py(50)), (120, 125, 132), width=2, dash=5, gap=4)
    if show_50:
        draw.text((right, py(50) - 8), "50%", fill=MUTED, font=font(9), anchor="ra")

    slot = (right - left) / len(values)
    bar_w = max(slot * 0.45, 4)
    rng = random.Random(132)
    for index, value in enumerate(values):
        x = left + slot * (index + 0.5)
        y = py(value)
        draw.rectangle(
            [x - bar_w / 2, min(y, py(50)), x + bar_w / 2, max(y, py(50))],
            fill=blend(BG, BLUE, 0.65),
        )
        error = rng.uniform(1.4, 2.4)
        draw.line([(x, py(value - error)), (x, py(value + error))], fill=(120, 125, 132), width=1)
        draw.line([(x - 3, py(value - error)), (x + 3, py(value - error))], fill=(120, 125, 132), width=1)
        draw.line([(x - 3, py(value + error)), (x + 3, py(value + error))], fill=(120, 125, 132), width=1)
        if labels[index] is not None:
            draw.text((x, bottom + 8), labels[index], fill=MUTED, font=font(9), anchor="ma")


def render_hour_weekday() -> Path:
    width, height = 900, 480
    image, draw = canvas(
        width,
        height,
        "Up-move probability by hour and weekday",
        "The bars sit around the coin-flip line; the spread is inside the noise",
    )
    rng = random.Random(131)
    hourly = [50 + rng.uniform(-2.7, 2.7) for _ in range(24)]
    weekdays = [50 + rng.uniform(-1.9, 1.9) for _ in range(5)]
    hour_labels = [f"{hour:02d}" if hour % 3 == 0 else None for hour in range(24)]
    day_labels = ["Mon", "Tue", "Wed", "Thu", "Fri"]

    draw_probability_panel(
        draw,
        (60, 110, 590, 410),
        hourly,
        hour_labels,
        "By hour (UTC)",
        True,
    )
    draw_probability_panel(
        draw,
        (620, 110, 860, 410),
        weekdays,
        day_labels,
        "By weekday",
        False,
        show_50=False,
    )
    footer(
        draw,
        width,
        height,
        "In testing the differences did not survive as a timing rule; the sample counts matter as much as the bars.",
    )
    out = OUT / "hour-weekday-probability.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    image.save(out, format="PNG", optimize=True)
    print(f"wrote {out}")
    return out


def render_big_trade_footprint() -> Path:
    width, height = 900, 540
    image, draw = canvas(
        width,
        height,
        "Volume without open interest is a footprint",
        "A volume/OI spike flags large participation; it does not say direction",
    )
    left, right = 90, 850
    price_top, price_bottom = 110, 300
    volume_top, volume_bottom = 316, 392
    ratio_top, ratio_bottom = 408, 486
    count = 48
    spike = 30

    candles = make_ohlc(100.0, 0.0012, 0.016, count, seed=141)
    price_low = min(candle[2] for candle in candles)
    price_high = max(candle[1] for candle in candles)
    pad = (price_high - price_low) * 0.07
    price_low -= pad
    price_high += pad

    def px(index: float) -> float:
        return left + (index + 0.5) / count * (right - left)

    def py(value: float) -> float:
        return price_bottom - (value - price_low) / (price_high - price_low) * (price_bottom - price_top)

    draw.text((left, price_top - 16), "price", fill=INK, font=font(12, bold=True))
    slot = (right - left) / count
    body = max(slot * 0.55, 3)
    for index, (open_, high, low, close) in enumerate(candles):
        x = px(index)
        color = GREEN if close >= open_ else RED
        draw.line([(x, py(high)), (x, py(low))], fill=color, width=1)
        y_top = min(py(open_), py(close))
        y_bottom = max(py(open_), py(close))
        draw.rectangle([x - body / 2, y_top, x + body / 2, max(y_bottom, y_top + 2)], fill=color)

    rng = random.Random(142)
    volumes = [rng.uniform(70, 130) for _ in range(count)]
    volumes[spike] *= 3.1
    oi = [100 + 0.35 * index + rng.uniform(-1.2, 1.2) for index in range(count)]
    ratios = [volume / value for volume, value in zip(volumes, oi)]
    average = sum(ratios) / len(ratios)
    threshold = average * 1.5

    draw.text((left, volume_top - 16), "volume", fill=INK, font=font(12, bold=True))
    for index, volume in enumerate(volumes):
        x = px(index)
        bar_h = volume / max(volumes) * (volume_bottom - volume_top)
        draw.rectangle([x - body / 2, volume_bottom - bar_h, x + body / 2, volume_bottom], fill=blend(BG, BLUE, 0.55))

    draw.text((left, ratio_top - 16), "volume / OI", fill=INK, font=font(12, bold=True))
    ratio_low, ratio_high = 0.5, max(ratios) * 1.08

    def ry(value: float) -> float:
        return ratio_bottom - (value - ratio_low) / (ratio_high - ratio_low) * (ratio_bottom - ratio_top)

    draw.rectangle([left, ratio_top, right, ratio_bottom], fill=CARD, outline=GRID)
    dashed(draw, (left, ry(threshold)), (right, ry(threshold)), RED, width=2, dash=6, gap=5)
    draw.text((right - 4, ry(threshold) - 14), "1.5× average", fill=RED, font=font(10, bold=True), anchor="ra")
    ratio_points = [(px(index), ry(value)) for index, value in enumerate(ratios)]
    draw.line(ratio_points, fill=PURPLE, width=2, joint="curve")

    spike_x = px(spike)
    dashed(draw, (spike_x, price_top), (spike_x, ratio_bottom), ORANGE, width=2, dash=6, gap=5)
    draw.polygon([(spike_x - 5, price_top - 8), (spike_x + 5, price_top - 8), (spike_x, price_top - 16)], fill=ORANGE)
    draw.text((spike_x + 8, price_top - 18), "spike", fill=ORANGE, font=font(11, bold=True))
    draw.text((spike_x + 8, price_top - 2), "direction not implied", fill=MUTED, font=font(10))

    footer(
        draw,
        width,
        height,
        "The flag says a large player may be active; it does not say which way.",
    )
    out = OUT / "big-trade-footprint.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    image.save(out, format="PNG", optimize=True)
    print(f"wrote {out}")
    return out


def render_crowding_dashboard() -> Path:
    width, height = 900, 440
    image, draw = canvas(
        width,
        height,
        "Crowding is what most participants see",
        "Three common inputs combined into one confirmation score",
    )

    rows = [
        ("RSI (14)", "74", "overbought", 74 / 100, RED),
        ("Bollinger position", "0.92", "near the upper band", 0.92, ORANGE),
        ("Distance from 50/200 MA", "+6.8%", "stretched above both", 0.84, ORANGE),
    ]
    for index, (name, value, note, position, color) in enumerate(rows):
        y0 = 112 + index * 96
        draw.rounded_rectangle([60, y0, 560, y0 + 76], radius=10, fill=CARD, outline=GRID)
        draw.text((76, y0 + 12), name, fill=INK, font=font(14, bold=True))
        draw.text((544, y0 + 12), value, fill=color, font=font(14, bold=True), anchor="ra")
        draw.text((76, y0 + 36), note, fill=MUTED, font=font(11))
        track_x0, track_x1, track_y = 76, 544, y0 + 58
        draw.rounded_rectangle([track_x0, track_y - 4, track_x1, track_y + 4], radius=4, fill=(232, 234, 230))
        marker_x = track_x0 + position * (track_x1 - track_x0)
        draw.rounded_rectangle([track_x0, track_y - 4, marker_x, track_y + 4], radius=4, fill=blend(BG, color, 0.55))
        draw.ellipse([marker_x - 5, track_y - 7, marker_x + 5, track_y + 7], fill=color)

    card_x0, card_x1 = 590, 860
    draw.rounded_rectangle([card_x0, 112, card_x1, 388], radius=10, fill=CARD, outline=GRID)
    draw.text(((card_x0 + card_x1) / 2, 126), "Crowding score", fill=INK, font=font(14, bold=True), anchor="ma")

    cx, cy, radius = (card_x0 + card_x1) / 2, 300, 100
    draw.arc([cx - radius, cy - radius, cx + radius, cy + radius], 180, 252, fill=GREEN, width=16)
    draw.arc([cx - radius, cy - radius, cx + radius, cy + radius], 252, 306, fill=ORANGE, width=16)
    draw.arc([cx - radius, cy - radius, cx + radius, cy + radius], 306, 360, fill=RED, width=16)

    score = 78
    angle = math.radians(180 + score / 100 * 180)
    needle_x = cx + math.cos(angle) * (radius - 20)
    needle_y = cy + math.sin(angle) * (radius - 20)
    draw.line([(cx, cy), (needle_x, needle_y)], fill=INK, width=4)
    draw.ellipse([cx - 7, cy - 7, cx + 7, cy + 7], fill=INK)
    draw.text((cx, cy + 22), f"{score} / 100", fill=INK, font=font(18, bold=True), anchor="ma")
    draw.text((cx, cy + 46), "confirmation, not timing", fill=MUTED, font=font(11), anchor="ma")

    for value, label in ((0, "0"), (50, "50"), (100, "100")):
        angle = math.radians(180 + value / 100 * 180)
        tx = cx + math.cos(angle) * (radius + 16)
        ty = cy + math.sin(angle) * (radius + 16)
        draw.text((tx, ty), label, fill=MUTED, font=font(9), anchor="mm")

    footer(
        draw,
        width,
        height,
        "The score says the setup is widely visible; it does not say when it reverses.",
    )
    out = OUT / "indicator-crowding-dashboard.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    image.save(out, format="PNG", optimize=True)
    print(f"wrote {out}")
    return out


def render_narratives() -> Path:
    width, height = 900, 520
    image, draw = canvas(
        width,
        height,
        "Leadership is visible; persistence is the open question",
        "Relative strength across one narrative basket, one line per asset",
    )
    left, top, right, bottom = 80, 120, 620, 430
    y_min, y_max = 84, 134
    count = 60

    def py(value: float) -> float:
        return bottom - (value - y_min) / (y_max - y_min) * (bottom - top)

    for value in (90, 100, 110, 120, 130):
        y = py(value)
        draw.line([(left, y), (right, y)], fill=GRID)
        draw.text((left - 12, y), str(value), fill=MUTED, font=font(10), anchor="rm")
    draw.text((left - 12, top - 18), "RS", fill=MUTED, font=font(11, bold=True), anchor="lm")

    series = [
        ("AI", [96, 99, 104, 113, 126], GREEN),
        ("DeFi", [100, 104, 99, 108, 112], BLUE),
        ("RWA", [99, 100, 101, 103, 108], ORANGE),
        ("Gaming", [104, 101, 108, 103, 106], PURPLE),
        ("L2", [98, 97, 102, 105, 103], (74, 122, 150)),
        ("Oracles", [101, 106, 104, 100, 98], MUTED),
        ("Memes", [108, 112, 104, 96, 91], RED),
    ]

    def path(values, seed: int, noise: float = 0.55):
        rng = random.Random(seed)
        points = []
        for index in range(count):
            t = index / (count - 1) * (len(values) - 1)
            base = min(int(t), len(values) - 2)
            fraction = t - base
            value = values[base] * (1 - fraction) + values[base + 1] * fraction
            value += rng.uniform(-noise, noise)
            points.append((left + index / (count - 1) * (right - left), py(value)))
        return points

    for index, (name, values, color) in enumerate(series):
        points = path(values, seed=170 + index)
        draw.line(points, fill=color, width=2, joint="curve")
        end_x, end_y = points[-1]
        draw.ellipse([end_x - 3, end_y - 3, end_x + 3, end_y + 3], fill=color)
        if name in ("AI", "Memes"):
            label = "leader" if name == "AI" else "laggard"
            offset = -14 if name == "AI" else 16
            draw.text((end_x - 6, end_y + offset), label, fill=color, font=font(10, bold=True), anchor="ra")

    dashed(draw, (right, top), (right, bottom), ORANGE, width=1, dash=4, gap=4)
    draw.text((right - 4, top - 18), "now", fill=ORANGE, font=font(10, bold=True), anchor="ra")

    card_x0, card_x1 = 646, 862
    draw.rounded_rectangle([card_x0, 106, card_x1, 404], radius=10, fill=CARD, outline=GRID)
    draw.text((card_x0 + 14, 120), "Rank today", fill=INK, font=font(14, bold=True))
    draw.text((card_x0 + 14, 140), "retrospective, not predictive", fill=MUTED, font=font(10))

    ranked = sorted(series, key=lambda item: item[1][-1], reverse=True)
    for rank, (name, values, color) in enumerate(ranked):
        y = 168 + rank * 32
        if rank == 0:
            draw.rounded_rectangle([card_x0 + 8, y - 7, card_x1 - 8, y + 25], radius=7, fill=GREEN_FILL, outline=GREEN)
        draw.text((card_x0 + 18, y), str(rank + 1), fill=MUTED, font=font(10, bold=True))
        draw.rounded_rectangle([card_x0 + 38, y + 1, card_x0 + 50, y + 13], radius=3, fill=color)
        draw.text((card_x0 + 60, y - 1), name, fill=INK, font=font(12, bold=rank == 0))
        draw.text((card_x1 - 18, y - 1), f"{values[-1]:.0f}", fill=color, font=font(12, bold=True), anchor="ra")

    draw.text((card_x0 + 14, 380), "tomorrow?", fill=ORANGE, font=font(11, bold=True))
    footer(
        draw,
        width,
        height,
        "The ranking is a map of what already happened; persistence still needs a forward test.",
    )
    out = OUT / "narratives-rotation.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    image.save(out, format="PNG", optimize=True)
    print(f"wrote {out}")
    return out


def render_asset_offset() -> Path:
    width, height = 900, 540
    image, draw = canvas(
        width,
        height,
        "A lag can always be fitted after the fact",
        "The same leading series, shifted and rescaled by hand",
    )
    left, top, right, bottom = 80, 120, 860, 390

    for step in (0.0, 0.25, 0.5, 0.75, 1.0):
        y = bottom - step * (bottom - top)
        draw.line([(left, y), (right, y)], fill=GRID)
    draw.text((left - 12, top), "high", fill=MUTED, font=font(10), anchor="rm")
    draw.text((left - 12, bottom), "low", fill=MUTED, font=font(10), anchor="rm")
    draw.text((left, top - 18), "normalized, rescaled", fill=MUTED, font=font(10))

    def make_series(peaks, slope: float, seed: int, noise: float = 0.015):
        rng = random.Random(seed)
        values = []
        for index in range(80):
            x = index / 79
            value = 0.18 + slope * x
            for center, height, spread in peaks:
                value += height * math.exp(-((x - center) / spread) ** 2)
            value += rng.uniform(-noise, noise)
            values.append(value)
        low, high = min(values), max(values)
        return [(value - low) / (high - low) for value in values]

    m2 = make_series(
        [(0.18, 0.45, 0.045), (0.48, 0.55, 0.05), (0.78, 0.62, 0.045)],
        slope=0.10,
        seed=181,
    )
    asset = make_series(
        [(0.26, 0.40, 0.05), (0.56, 0.48, 0.05), (0.86, 0.56, 0.05)],
        slope=0.08,
        seed=182,
        noise=0.020,
    )

    def px(index: int) -> float:
        return left + index / 79 * (right - left)

    def py(value: float) -> float:
        return bottom - value * (bottom - top)

    m2_points = [(px(index), py(value)) for index, value in enumerate(m2)]
    asset_points = [(px(index), py(value)) for index, value in enumerate(asset)]
    draw.line(m2_points, fill=ORANGE, width=3, joint="curve")
    draw.line(asset_points, fill=BLUE, width=3, joint="curve")

    draw.line([(left + 6, 108), (left + 42, 108)], fill=ORANGE, width=3)
    draw.text((left + 50, 101), "M2 (shifted +42 d, rescaled)", fill=ORANGE, font=font(11, bold=True))
    draw.line([(left + 250, 108), (left + 286, 108)], fill=BLUE, width=3)
    draw.text((left + 294, 101), "risk asset", fill=BLUE, font=font(11, bold=True))

    for m2_index, asset_index in ((14, 21), (38, 45), (62, 69)):
        x0, x1 = px(m2_index), px(asset_index)
        dashed(draw, (x0, top), (x0, bottom), ORANGE, width=1, dash=4, gap=4)
        dashed(draw, (x1, top), (x1, bottom), BLUE, width=1, dash=4, gap=4)
        y = top + 34
        draw.line([(x0 + 4, y), (x1 - 4, y)], fill=INK, width=1)
        draw.polygon([(x0 + 4, y), (x0 + 11, y - 4), (x0 + 11, y + 4)], fill=INK)
        draw.polygon([(x1 - 4, y), (x1 - 11, y - 4), (x1 - 11, y + 4)], fill=INK)
        if m2_index == 14:
            draw.text(((x0 + x1) / 2, y - 12), "42 d", fill=INK, font=font(10, bold=True), anchor="ma")

    draw.text((px(14) - 6, py(m2[14]) - 16), "leader", fill=ORANGE, font=font(10, bold=True), anchor="ra")
    draw.text((px(69) + 4, py(asset[69]) - 18), "follows", fill=BLUE, font=font(10, bold=True), anchor="la")

    draw.rounded_rectangle([80, 410, 860, 482], radius=10, fill=CARD, outline=GRID)
    draw.text((96, 420), "Manual inputs", fill=INK, font=font(12, bold=True))
    knobs = [("Offset (days)", "42"), ("Start", "-680,000"), ("Mult", "70,000")]
    for index, (label, value) in enumerate(knobs):
        x0 = 212 + index * 198
        draw.rounded_rectangle([x0, 418, x0 + 178, 472], radius=8, fill=ORANGE_FILL, outline=blend(ORANGE_FILL, ORANGE, 0.35))
        draw.text((x0 + 12, 425), label, fill=MUTED, font=font(10))
        draw.text((x0 + 12, 442), value, fill=ORANGE, font=font(15, bold=True))
    draw.text((846, 425), "not estimated", fill=ORANGE, font=font(10, bold=True), anchor="ra")

    footer(
        draw,
        width,
        height,
        "Two free parameters can fit the past. Evidence needs a lag fixed before the fact.",
    )
    out = OUT / "asset-with-offset-lag.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    image.save(out, format="PNG", optimize=True)
    print(f"wrote {out}")
    return out


def render_tick_unanimity() -> Path:
    width, height = 900, 560
    image, draw = canvas(
        width,
        height,
        "A flat candle is not always empty",
        "Tick count and direction separate a two-sided fight from a one-way repricing",
    )

    panels = [
        {
            "title": "Area of interest",
            "note": "flat candle, many ticks both ways",
            "open": 236,
            "close": 236,
            "high": 228,
            "low": 244,
            "body": 10,
            "color": ORANGE,
            "ticks": ["up", "down"] * 8,
            "ratio": "1.0x",
            "badge": "two-sided",
            "badge_color": ORANGE,
            "hint": "a fight at this price",
        },
        {
            "title": "Agreement",
            "note": "large candle, one-way ticks",
            "open": 275,
            "close": 175,
            "high": 152,
            "low": 300,
            "body": 34,
            "color": GREEN,
            "ticks": ["up"] * 9 + ["down"],
            "ratio": "9.0x",
            "badge": "one-sided",
            "badge_color": GREEN,
            "hint": "repricing, often on news",
        },
        {
            "title": "No interest",
            "note": "flat candle, few ticks",
            "open": 238,
            "close": 234,
            "high": 228,
            "low": 248,
            "body": 10,
            "color": MUTED,
            "ticks": ["up", "down"],
            "ratio": "1.0x",
            "badge": "2 ticks",
            "badge_color": MUTED,
            "hint": "quiet, no fight here",
        },
    ]

    for index, panel in enumerate(panels):
        x0 = 55 + index * 270
        x1 = x0 + 250
        y0, y1 = 92, 486
        cx = (x0 + x1) / 2
        draw.rounded_rectangle([x0, y0, x1, y1], radius=10, fill=CARD, outline=GRID)
        draw.text((x0 + 14, y0 + 12), panel["title"], fill=INK, font=font(15, bold=True))
        draw.text((x0 + 14, y0 + 34), panel["note"], fill=MUTED, font=font(10))

        draw.line([(cx, panel["high"]), (cx, panel["low"])], fill=panel["color"], width=2)
        body_top = min(panel["open"], panel["close"])
        body_bottom = max(body_top + 8, max(panel["open"], panel["close"]))
        draw.rectangle(
            [cx - panel["body"] / 2, body_top, cx + panel["body"] / 2, body_bottom],
            fill=panel["color"],
        )

        draw.text((x0 + 14, 310), "ticks inside the candle", fill=MUTED, font=font(10, bold=True))
        ticks = panel["ticks"]
        spacing = min(24, 168 / len(ticks))
        total_width = spacing * len(ticks)
        start_x = cx - total_width / 2 + spacing / 2
        for tick_index, direction in enumerate(ticks):
            tick_x = start_x + tick_index * spacing
            color = GREEN if direction == "up" else RED
            height = 26 if index == 1 else (22 if index == 0 else 18)
            draw.line([(tick_x, 330), (tick_x, 330 + height)], fill=color, width=2)
            body_h = max(height * 0.55, 5)
            draw.rectangle([tick_x - 3, 330 + (height - body_h) / 2, tick_x + 3, 330 + (height + body_h) / 2], fill=color)

        up = ticks.count("up")
        down = ticks.count("down")
        draw.text((x0 + 14, 376), f"up {up}  ·  down {down}  ·  {len(ticks)} ticks", fill=MUTED, font=font(10))
        draw.text((cx, 402), panel["ratio"], fill=panel["badge_color"], font=font(24, bold=True), anchor="ma")
        draw.text((cx, 426), "unanimity ratio", fill=MUTED, font=font(9), anchor="ma")

        badge_color = panel["badge_color"]
        draw.rounded_rectangle(
            [x0 + 24, 442, x1 - 24, 470],
            radius=8,
            fill=blend(CARD, badge_color, 0.12),
            outline=blend(CARD, badge_color, 0.45),
        )
        draw.text((cx, 456), panel["badge"], fill=badge_color, font=font(10, bold=True), anchor="mm")
        draw.text((cx, 476), panel["hint"], fill=MUTED, font=font(9), anchor="ma")

    footer(
        draw,
        width,
        height,
        "The ratio alone is not the signal: many two-sided ticks show interest, one-way ticks show agreement.",
    )
    out = OUT / "tick-unanimity-candles.png"
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
    render_cluster_latency()
    render_implied_path()
    render_oi_bands()
    render_supply_unlocks()
    render_hour_weekday()
    render_big_trade_footprint()
    render_crowding_dashboard()
    render_narratives()
    render_asset_offset()
    render_tick_unanimity()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
