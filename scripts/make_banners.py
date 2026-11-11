#!/usr/bin/env python3
"""Render the README header and one banner per theory.

The banners are presentation artifacts, not data. They are generated offline
with Pillow so the repository does not depend on an external image service:

    python3 scripts/make_banners.py

The theory list and titles are read from the numbered index in ``README.md``.
If a theory is added or renamed, rerun this script.
The small kicker under each title is a short editorial label, not a claim.
"""

from __future__ import annotations

import random
import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
README = ROOT / "README.md"
OUT = ROOT / "assets/banners"

W, H = 1600, 260
HEADER_H = 480

INK = (244, 247, 251)
MUTED = (147, 164, 190)
DIM = (90, 107, 132)
GOLD = (233, 184, 114)
TEAL = (110, 231, 216)
CORAL = (248, 113, 113)
BLUE = (125, 211, 252)
PURPLE = (196, 181, 253)
AMBER = (252, 211, 77)
ORANGE = (253, 186, 116)
ROSE = (253, 164, 175)
INDIGO = (165, 180, 252)
GREEN = (134, 239, 172)
SLATE = (203, 213, 225)

KICKERS = {
    "01": "CAPACITY-CONSTRAINED ARBITRAGE",
    "02": "LEVERAGE CROWDING",
    "03": "LIQUIDATION MAGNETS",
    "04": "VISUAL SENTIMENT",
    "05": "CRYPTO NEWS VELOCITY",
    "06": "MACRO REPRICING AND LEAD-LAG",
    "07": "LISTING EVENT STUDY",
    "08": "POSITIONING CROWDING",
    "09": "OPEN-INTEREST LEVELS",
    "10": "LIQUIDITY DISPLAY",
    "11": "INFORMED FLOW",
    "12": "SUPPLY PRESSURE",
    "13": "CALENDAR EFFECTS",
    "14": "WHALE FOOTPRINTS",
    "15": "FILTER SELECTION AND BIAS",
    "16": "ATTENTION LEAD-LAG",
    "17": "INDICATOR CONSENSUS",
    "18": "WEATHER AND MOOD",
    "19": "RELATIVE-STRENGTH ROTATION",
    "20": "MANUAL LEAD-LAG OVERLAY",
    "21": "TICK ACTIVITY, NOT TIME",
}

ACCENTS = {
    "01": TEAL,
    "02": BLUE,
    "03": CORAL,
    "04": GREEN,
    "05": PURPLE,
    "06": AMBER,
    "07": ORANGE,
    "08": ROSE,
    "09": INDIGO,
    "10": SLATE,
    "11": TEAL,
    "12": BLUE,
    "13": GREEN,
    "14": PURPLE,
    "15": AMBER,
    "16": ORANGE,
    "17": ROSE,
    "18": INDIGO,
    "19": TEAL,
    "20": AMBER,
    "21": PURPLE,
}


def font(size: int, bold: bool = False, condensed: bool = False) -> ImageFont.FreeTypeFont:
    name = "DejaVuSansCondensed-Bold.ttf" if bold and condensed else (
        "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    )
    path = Path("/usr/share/fonts/truetype/dejavu") / name
    if path.exists():
        return ImageFont.truetype(str(path), size=size)
    return ImageFont.load_default()


def fit_font(
    draw: ImageDraw.ImageDraw,
    text: str,
    max_width: int,
    max_size: int,
    min_size: int,
    bold: bool = True,
    condensed: bool = True,
) -> ImageFont.FreeTypeFont:
    for size in range(max_size, min_size - 1, -1):
        candidate = font(size, bold=bold, condensed=condensed)
        if draw.textlength(text, font=candidate) <= max_width:
            return candidate
    return font(min_size, bold=bold, condensed=condensed)


def gradient(width: int, height: int, top: tuple[int, int, int], bottom: tuple[int, int, int]) -> Image.Image:
    image = Image.new("RGB", (width, height))
    pixels = image.load()
    for y in range(height):
        t = y / max(height - 1, 1)
        colour = tuple(round(top[i] + (bottom[i] - top[i]) * t) for i in range(3))
        for x in range(width):
            pixels[x, y] = colour
    return image


def dot_grid(overlay: Image.Image, step: int = 44, alpha: int = 12) -> None:
    draw = ImageDraw.Draw(overlay)
    for y in range(step, overlay.height, step):
        for x in range(step, overlay.width, step):
            draw.ellipse((x - 1, y - 1, x + 1, y + 1), fill=(255, 255, 255, alpha))


def network(overlay: Image.Image, seed: int, box: tuple[int, int, int, int]) -> None:
    draw = ImageDraw.Draw(overlay)
    rng = random.Random(seed)
    left, top, right, bottom = box
    nodes = [
        (rng.randint(left, right), rng.randint(top, bottom))
        for _ in range(15)
    ]
    for index, (x, y) in enumerate(nodes):
        neighbours = sorted(
            (i for i in range(len(nodes)) if i != index),
            key=lambda i: (nodes[i][0] - x) ** 2 + (nodes[i][1] - y) ** 2,
        )[:2]
        for neighbour in neighbours:
            nx, ny = nodes[neighbour]
            draw.line((x, y, nx, ny), fill=(110, 231, 216, 28), width=1)
        radius = 4 if index % 5 else 6
        colour = (233, 184, 114, 120) if index % 5 == 0 else (110, 231, 216, 95)
        draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=colour)


def tracked(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    text: str,
    text_font: ImageFont.FreeTypeFont,
    fill: tuple[int, int, int, int],
    spacing: int = 2,
) -> None:
    x, y = xy
    for char in text:
        draw.text((x, y), char, font=text_font, fill=fill)
        x += draw.textlength(char, font=text_font) + spacing


def bottom_rule(overlay: Image.Image, accent: tuple[int, int, int]) -> None:
    draw = ImageDraw.Draw(overlay)
    width = overlay.width
    for x in range(width):
        t = x / max(width - 1, 1)
        colour = tuple(round(GOLD[i] + (accent[i] - GOLD[i]) * t) for i in range(3))
        draw.line((x, overlay.height - 6, x, overlay.height - 1), fill=colour + (210,))


def save(image: Image.Image, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    image.convert("RGB").save(path, optimize=True)
    print(f"wrote {path.relative_to(ROOT)} ({image.width}x{image.height})")


def read_theories() -> list[tuple[str, str]]:
    text = README.read_text(encoding="utf-8")
    pattern = re.compile(
        r"^(\d+)\. \*\*\[([^\]]+)\]\(#[^)]+\)\*\*<br>$",
        re.MULTILINE,
    )
    rows = [(f"{int(num):02d}", title) for num, title in pattern.findall(text)]
    assert len(rows) == 21, f"expected 21 theories in README, found {len(rows)}"
    return rows


def slug(title: str) -> str:
    value = title.lower().replace("&", "and")
    value = re.sub(r"[^a-z0-9]+", "-", value).strip("-")
    return value


def render_header() -> Path:
    image = gradient(W, HEADER_H, (10, 17, 31), (17, 28, 48)).convert("RGBA")
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    dot_grid(overlay, step=42, alpha=10)
    network(overlay, seed=7, box=(1220, 40, 1545, 355))
    draw = ImageDraw.Draw(overlay)

    draw.rectangle((72, 104, 80, 358), fill=GOLD + (255,))
    tracked(
        draw,
        (112, 104),
        "RESEARCH NOTEBOOK  ·  MARKET HYPOTHESES",
        font(17, bold=True),
        GOLD + (235,),
        spacing=2,
    )

    title = "Financial-Market-Theories"
    title_font = fit_font(draw, title, 1180, 82, 60)
    draw.text((108, 145), title, font=title_font, fill=INK + (255,))

    subtitle = "Falsifiable hypotheses about markets, each with code, data, and a verdict."
    draw.text((112, 262), subtitle, font=font(28), fill=MUTED + (255,))

    tracked(
        draw,
        (112, 368),
        "21 THEORIES  ·  CODE  ·  DATA  ·  VERDICTS",
        font(14, bold=True),
        (160, 178, 202, 230),
        spacing=2,
    )
    draw.text((1540, 368), "2026", font=font(14, bold=True), fill=DIM + (230,), anchor="ra")

    bottom_rule(overlay, TEAL)
    image = Image.alpha_composite(image, overlay)
    path = OUT / "readme-header.png"
    save(image, path)
    return path


def render_theory(num: str, title: str) -> Path:
    image = gradient(W, H, (11, 19, 34), (18, 30, 51)).convert("RGBA")
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    dot_grid(overlay, step=40, alpha=9)
    draw = ImageDraw.Draw(overlay)
    accent = ACCENTS[num]

    draw.rectangle((72, 52, 78, 198), fill=accent + (255,))

    title_font = fit_font(draw, title, 1120, 58, 38)
    draw.text((112, 64), title, font=title_font, fill=INK + (255,))
    tracked(
        draw,
        (114, 144),
        KICKERS[num],
        font(16, bold=True),
        MUTED + (235,),
        spacing=2,
    )

    draw.text(
        (114, 196),
        "FINANCIAL-MARKET-THEORIES",
        font=font(11, bold=True),
        fill=DIM + (220,),
    )

    bottom_rule(overlay, accent)

    image = Image.alpha_composite(image, overlay)
    path = OUT / f"{slug(title)}.png"
    save(image, path)
    return path


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    render_header()
    for num, title in read_theories():
        render_theory(num, title)


if __name__ == "__main__":
    main()
