#!/usr/bin/env python3
"""Compose the five sizing demos into one contact sheet.

The individual demo PNGs keep their native geometry. This script scales each
panel to the same height so the width differences (especially the two
column-sizing rules) are easy to compare.

Example
-------
    python3 scripts/make-demo-sheet.py --suffix 2026-10-29_11-04
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parent
DEFAULT_RESULTS = PROJECT / "results"

MODES = (
    ("fixed", "every cell the same size"),
    ("views-day", "size follows same-day views"),
    ("views-all", "size follows views across the week"),
    ("column-total", "column width follows the day's total views"),
    ("column-avg", "column width follows the day's average views"),
)


def load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        if bold
        else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ]
    for candidate in candidates:
        if Path(candidate).exists():
            return ImageFont.truetype(candidate, size=size)
    return ImageFont.load_default()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results-dir", type=Path, default=DEFAULT_RESULTS)
    parser.add_argument("--suffix", default="2026-10-29_11-04")
    parser.add_argument("--panel-height", type=int, default=900)
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="defaults to <results-dir>/thumbnail_grid_demo_all_sizings_<suffix>.png",
    )
    args = parser.parse_args()

    panels: list[tuple[str, str, Image.Image]] = []
    for mode, description in MODES:
        slug = mode.replace("-", "_")
        matches = [
            args.results_dir / f"thumbnail_grid_demo_{slug}_{args.suffix}{suffix}"
            for suffix in (".jpg", ".png")
        ]
        path = next((candidate for candidate in matches if candidate.exists()), None)
        if path is None:
            raise SystemExit(f"missing demo image: {matches[0]}")
        image = Image.open(path).convert("RGB")
        width = max(1, round(image.width * args.panel_height / image.height))
        panels.append((mode, description, image.resize((width, args.panel_height))))

    margin = 22
    gap = 18
    label_height = 30
    title_height = 74
    cell_width = max(panel.width for _, _, panel in panels)
    columns = 2
    rows = (len(panels) + columns - 1) // columns
    canvas_width = margin * 2 + columns * cell_width + (columns - 1) * gap
    canvas_height = (
        margin * 2
        + title_height
        + rows * (label_height + args.panel_height)
        + (rows - 1) * gap
    )
    canvas = Image.new("RGB", (canvas_width, canvas_height), (246, 246, 244))
    draw = ImageDraw.Draw(canvas)

    title_font = load_font(22, bold=True)
    subtitle_font = load_font(12)
    label_font = load_font(14, bold=True)
    note_font = load_font(10)

    draw.text(
        (margin, margin),
        "Five sizing rules on the same week",
        fill=(25, 25, 25),
        font=title_font,
    )
    count = None
    fixed_manifest = (
        args.results_dir / f"thumbnail_grid_demo_fixed_{args.suffix}.json"
    )
    if fixed_manifest.exists():
        try:
            manifest = json.loads(fixed_manifest.read_text(encoding="utf-8"))
            count = sum(len(items) for items in manifest.get("days", {}).values())
        except (OSError, json.JSONDecodeError):
            count = None
    count_text = f"{count} thumbnails" if count else "same videos in every panel"
    draw.text(
        (margin, margin + 32),
        f"{args.suffix.replace('_', ' to ')} · {count_text} · "
        "only the sizing rule changes between panels",
        fill=(80, 80, 80),
        font=subtitle_font,
    )

    y = margin + title_height
    for index, (mode, description, panel) in enumerate(panels):
        row = index // columns
        column = index % columns
        x = margin + column * (cell_width + gap)
        panel_y = y + row * (label_height + args.panel_height + gap)
        draw.rectangle(
            [x, panel_y, x + cell_width, panel_y + label_height - 4],
            fill=(226, 229, 224),
        )
        draw.text(
            (x + 8, panel_y + 4),
            f"{mode}  ·  {description}",
            fill=(30, 30, 30),
            font=label_font,
        )
        panel_x = x + (cell_width - panel.width) // 2
        canvas.paste(panel, (panel_x, panel_y + label_height))

    footer = (
        "Source: cached public YouTube thumbnails, 29 Oct to 4 Nov 2026 · "
        "members-only uploads excluded · sizing is presentation, not sentiment"
    )
    draw.text(
        (margin, canvas_height - margin + 2),
        footer,
        fill=(95, 95, 95),
        font=note_font,
    )

    output = args.output or (
        args.results_dir / f"thumbnail_grid_demo_all_sizings_{args.suffix}.png"
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output, format="PNG", optimize=True)
    print(f"wrote {output} ({canvas.width}x{canvas.height}, {len(panels)} panels)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
