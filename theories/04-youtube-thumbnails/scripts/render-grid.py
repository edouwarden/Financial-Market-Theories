#!/usr/bin/env python3
"""Render a YouTube thumbnail grid from a cached snapshot.

This is the offline counterpart to the Tkinter app in ``test/``. It reads the
per-channel metadata files and the thumbnail cache, then writes one image.
No network access is required, so the same snapshot can be re-rendered with
different layouts and sizing rules. A ``.jpg``/``.jpeg`` output is saved as
JPEG; anything else is saved as PNG.

Examples
--------
    python3 scripts/render-grid.py --date 2025-09-04 --sizing views-day
    python3 scripts/render-grid.py --start 2025-09-03 --end 2025-09-05 \\
        --sizing views-all --output results/thumbnail_grid_views_all.png
    python3 scripts/render-grid.py --start 2026-08-04 --end 2026-11-04 \\
        --metadata-dir test/youtube_metadata_window \\
        --cache-dir test/youtube_cache_window --layout calendar
    python3 scripts/render-grid.py --start 2026-08-04 --end 2026-11-04 \\
        --layout timeline --sizing views-all --per-row 16
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageDraw, ImageFont, ImageOps

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parent
DEFAULT_METADATA = PROJECT / "test" / "youtube_metadata"
DEFAULT_CACHE = PROJECT / "test" / "youtube_cache"
DEFAULT_CHANNELS = PROJECT / "data" / "channels.txt"
DEFAULT_OUTPUT = PROJECT / "results" / "thumbnail_grid.png"

SIZING_CHOICES = (
    "fixed",
    "views-day",
    "views-all",
    "column-total",
    "column-avg",
)

# Used only when --channels-file is missing. The curated file is the normal
# control surface; this keeps the imported 80+ list from quietly coming back.
FALLBACK_EXCLUDED = {
    "Hasheur",
    "JulienRoman",
    "MonsieurTK",
    "lesroisdubitcoin",
    "grandanglebitcoin",
    "CryptoLeTrone",
    "UndergroundTradingFr",
    "Cryptolyze",
    "CryptoFutur",
    "insydercrypto",
}


def find_thumbnail(cache_dir: Path, video_id: str) -> Path | None:
    for suffix in (".jpg", ".jpeg", ".png"):
        path = cache_dir / f"{video_id}{suffix}"
        if path.exists():
            return path
    return None


def save_canvas(canvas: Image.Image, output: Path) -> None:
    """PNG for text-heavy calendar/timeline sheets; JPEG for demo grids."""
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.suffix.lower() in (".jpg", ".jpeg"):
        canvas.save(output, format="JPEG", quality=90, optimize=True, subsampling=1)
    else:
        canvas.save(output, format="PNG", optimize=True)


def parse_date(value: str) -> date:
    return date.fromisoformat(value)


def display_path(path: Path) -> str:
    """Prefer a project-relative path so manifests do not leak a home folder."""
    try:
        return str(path.resolve().relative_to(PROJECT))
    except ValueError:
        return str(path)


def read_channel_list(path: Path) -> set[str] | None:
    if not path.exists():
        return None
    channels = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0].strip()
        if line:
            channels.add(line)
    return channels or None


def video_title(video: dict) -> str:
    title = video.get("title")
    if isinstance(title, dict):
        runs = title.get("runs") or []
        if runs and isinstance(runs[0], dict):
            return str(runs[0].get("text", ""))
    return str(title or "")


def load_videos(
    metadata_dir: Path,
    cache_dir: Path,
    include: set[str] | None,
    exclude: set[str],
) -> list[dict]:
    if not metadata_dir.exists():
        raise SystemExit(f"metadata directory not found: {metadata_dir}")
    if not cache_dir.exists():
        raise SystemExit(f"thumbnail cache not found: {cache_dir}")

    videos: list[dict] = []
    seen: set[tuple[str, str]] = set()
    for path in sorted(metadata_dir.glob("*_videos.json")):
        channel = path.name[: -len("_videos.json")]
        if include is not None and channel not in include:
            continue
        if channel in exclude:
            continue
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            print(f"warning: skipping {path.name}: {exc}", file=sys.stderr)
            continue
        if not isinstance(raw, list):
            print(f"warning: skipping {path.name}: not a list", file=sys.stderr)
            continue
        for item in raw:
            if not isinstance(item, dict):
                continue
            video_id = str(item.get("video_id") or "")
            published = item.get("published_at")
            if not video_id or not isinstance(published, (int, float)):
                continue
            if (channel, video_id) in seen:
                continue
            thumb_path = find_thumbnail(cache_dir, video_id)
            if thumb_path is None:
                continue
            seen.add((channel, video_id))
            videos.append(
                {
                    "channel": channel,
                    "video_id": video_id,
                    "published_at": int(published),
                    "date": datetime.fromtimestamp(
                        published / 1000, tz=timezone.utc
                    ).date(),
                    "views": int(item.get("view_count") or 0),
                    "title": video_title(item),
                    "thumbnail": str(thumb_path),
                }
            )
    return videos


def human_views(value: int) -> str:
    if value >= 1_000_000:
        return f"{value / 1_000_000:.1f}M"
    if value >= 1_000:
        return f"{value / 1_000:.0f}K"
    return str(value)


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


def fit_thumbnail(path: str, width: int, height: int) -> Image.Image:
    image = Image.open(path).convert("RGB")
    return ImageOps.fit(image, (width, height), Image.Resampling.LANCZOS)


def draw_label(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    width: int,
    channel: str,
    views: int,
) -> None:
    font = load_font(max(9, min(13, width // 18)))
    text = f"{channel}  ·  {human_views(views)}"
    if draw.textlength(text, font=font) > width:
        while text and draw.textlength(text + "…", font=font) > width:
            text = text[:-1]
        text = text.rstrip() + "…"
    draw.text((x, y), text, fill=(60, 60, 60), font=font)


def wrap_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.FreeTypeFont,
    max_width: int,
) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if current and draw.textlength(candidate, font=font) > max_width:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines or [""]


def cell_geometry(
    videos_by_day: dict[date, list[dict]],
    days: list[date],
    sizing: str,
    base_width: int,
) -> tuple[dict[date, int], dict[date, int], int]:
    """Return column widths and per-day row heights (without header)."""
    column_widths: dict[date, int] = {}
    row_heights: dict[date, int] = {}

    if sizing == "column-total":
        totals = {day: sum(v["views"] for v in videos_by_day[day]) for day in days}
        max_total = max(totals.values()) if totals else 1
        for day in days:
            ratio = totals[day] / max_total if max_total else 1
            column_widths[day] = max(int(base_width * ratio), base_width // 2)
            row_heights[day] = int(column_widths[day] * 9 / 16)
        return column_widths, row_heights, max(row_heights.values(), default=0)

    if sizing == "column-avg":
        averages = {}
        for day in days:
            values = [v["views"] for v in videos_by_day[day]]
            averages[day] = sum(values) / len(values) if values else 0
        max_avg = max(averages.values()) if averages else 1
        for day in days:
            ratio = averages[day] / max_avg if max_avg else 1
            column_widths[day] = max(int(base_width * ratio), base_width // 2)
            row_heights[day] = int(column_widths[day] * 9 / 16)
        return column_widths, row_heights, max(row_heights.values(), default=0)

    for day in days:
        column_widths[day] = base_width
        row_heights[day] = int(base_width * 9 / 16)
    return column_widths, row_heights, int(base_width * 9 / 16)


def render_single_day(
    videos: list[dict],
    day: date,
    sizing: str,
    base_width: int,
    columns: int,
    output: Path,
    title: str | None,
) -> None:
    """Render one day as a compact multi-column grid."""
    if not videos:
        raise SystemExit("no cached videos found for the selected date")

    margin = 18
    gap = 10
    label_height = 22
    footer_height = 28
    columns = max(1, columns)
    rows = math.ceil(len(videos) / columns)

    logo_font = load_font(20, bold=True)
    header_font = load_font(13, bold=True)
    footer_font = load_font(11)

    # Wrap the title across the full grid width.
    grid_width = columns * base_width + (columns - 1) * gap
    title_lines = (
        wrap_text(ImageDraw.Draw(Image.new("RGB", (1, 1))), title, logo_font, grid_width)
        if title
        else []
    )
    title_height = len(title_lines) * 27 + (10 if title_lines else 0)

    header_height = 48
    cell_height = int(base_width * 9 / 16) + label_height
    canvas_width = margin * 2 + grid_width
    canvas_height = (
        margin * 2
        + title_height
        + header_height
        + rows * cell_height
        + footer_height
    )

    canvas = Image.new("RGB", (canvas_width, canvas_height), (246, 246, 244))
    draw = ImageDraw.Draw(canvas)

    y = margin
    for line in title_lines:
        draw.text((margin, y), line, fill=(25, 25, 25), font=logo_font)
        y += 27

    total_views = sum(v["views"] for v in videos)
    header = f"{day.isoformat()}   {len(videos)} videos   {human_views(total_views)} views"
    draw.text((margin, y + 6), header, fill=(55, 55, 55), font=header_font)
    y += header_height

    peak = max((v["views"] for v in videos), default=1) or 1
    thumb_height = int(base_width * 9 / 16)

    for index, video in enumerate(videos):
        col = index % columns
        row = index // columns
        cell_x = margin + col * (base_width + gap)
        cell_y = y + row * cell_height

        width = base_width
        height = thumb_height
        if sizing in ("views-day", "views-all"):
            ratio = max(0.28, min(1.0, video["views"] / peak))
            width = max(int(base_width * ratio), int(base_width * 0.28))
            height = max(int(width * 9 / 16), 1)

        thumb_x = cell_x + (base_width - width) // 2
        thumb_y = cell_y + (thumb_height - height) // 2
        try:
            image = fit_thumbnail(video["thumbnail"], width, height)
            canvas.paste(image, (thumb_x, thumb_y))
        except Exception as exc:  # pragma: no cover - defensive
            draw.rectangle(
                [thumb_x, thumb_y, thumb_x + width, thumb_y + height],
                fill=(200, 200, 200),
            )
            draw.text(
                (thumb_x + 4, thumb_y + 4),
                f"missing: {exc}",
                fill=(80, 80, 80),
                font=footer_font,
            )
        draw_label(
            draw,
            cell_x,
            cell_y + thumb_height + 3,
            base_width,
            video["channel"],
            video["views"],
        )

    footer = (
        "Cached YouTube thumbnails · size follows the selected rule · "
        "not a sentiment score"
    )
    draw.text(
        (margin, canvas_height - margin - 14),
        footer,
        fill=(95, 95, 95),
        font=footer_font,
    )

    save_canvas(canvas, output)
    print(
        f"wrote {output} ({canvas.width}x{canvas.height}, "
        f"{len(videos)} thumbnails, {columns} columns)"
    )


def render_timeline(
    videos: list[dict],
    start: date,
    end: date,
    sizing: str,
    base_width: int,
    per_row: int,
    output: Path,
    title: str | None,
) -> None:
    """Render a long window as one timeline block per channel.

    Each channel gets a header and one or more rows of thumbnails, oldest on
    the left. This is the readable alternative to 90+ daily columns.
    """
    if not videos:
        raise SystemExit("no cached videos found for the selected window")
    if sizing not in ("fixed", "views-day", "views-all"):
        raise SystemExit(
            "timeline layout supports --sizing fixed, views-day, or views-all"
        )

    by_channel: dict[str, list[dict]] = defaultdict(list)
    for video in videos:
        by_channel[video["channel"]].append(video)
    for items in by_channel.values():
        items.sort(key=lambda v: (v["published_at"], v["video_id"]))

    channels = sorted(by_channel)
    per_row = max(1, per_row)
    margin = 20
    gap = 8
    block_gap = 18
    header_height = 26
    label_height = 20
    cell_width = max(90, base_width)
    thumb_height = int(cell_width * 9 / 16)

    title_font = load_font(21, bold=True)
    overview_font = load_font(12, bold=True)
    note_font = load_font(10)
    channel_font = load_font(14, bold=True)
    label_font = load_font(9)

    grid_width = per_row * cell_width + (per_row - 1) * gap
    canvas_width = margin * 2 + grid_width
    probe = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    title_lines = (
        wrap_text(probe, title, title_font, canvas_width - margin * 2) if title else []
    )
    top_banner = len(title_lines) * 27 + (10 if title_lines else 0)
    overview_height = 44

    block_heights: dict[str, int] = {}
    for channel in channels:
        rows = math.ceil(len(by_channel[channel]) / per_row)
        block_heights[channel] = (
            header_height + rows * (thumb_height + label_height + 3) + block_gap
        )

    total_height = (
        margin * 2
        + top_banner
        + overview_height
        + sum(block_heights.values())
    )
    canvas = Image.new("RGB", (canvas_width, total_height), (246, 246, 244))
    draw = ImageDraw.Draw(canvas)

    y = margin
    for line in title_lines:
        draw.text((margin, y), line, fill=(25, 25, 25), font=title_font)
        y += 27

    total_views = sum(v["views"] for v in videos)
    overview = (
        f"{start.isoformat()} → {end.isoformat()}   "
        f"{len(videos)} videos   {len(channels)} channels   "
        f"{human_views(total_views)} views"
    )
    draw.text((margin, y + 4), overview, fill=(45, 45, 45), font=overview_font)
    rule_text = {
        "fixed": "fixed cell size",
        "views-day": "size follows same-day views",
        "views-all": "size follows views across the whole window",
    }[sizing]
    draw.text(
        (margin, y + 24),
        f"Each block is one channel · oldest → newest · {rule_text}",
        fill=(85, 85, 85),
        font=note_font,
    )
    y += overview_height

    global_peak = max((v["views"] for v in videos), default=1) or 1
    day_peaks: dict[date, int] = defaultdict(int)
    for video in videos:
        day_peaks[video["date"]] = max(day_peaks[video["date"]], video["views"])

    for channel in channels:
        items = by_channel[channel]
        draw.rectangle(
            [margin, y, margin + grid_width, y + header_height - 5],
            fill=(226, 229, 224),
        )
        channel_total = sum(v["views"] for v in items)
        draw.text(
            (margin + 8, y + 5),
            f"{channel}   {len(items)} videos   {human_views(channel_total)} views",
            fill=(30, 30, 30),
            font=channel_font,
        )
        y += header_height

        for row_start in range(0, len(items), per_row):
            row = items[row_start : row_start + per_row]
            for column, video in enumerate(row):
                cell_x = margin + column * (cell_width + gap)
                if sizing == "fixed":
                    ratio = 1.0
                elif sizing == "views-day":
                    peak = day_peaks[video["date"]] or 1
                    ratio = video["views"] / peak
                else:
                    ratio = video["views"] / global_peak
                ratio = max(0.28, min(1.0, ratio))
                width = max(int(cell_width * ratio), int(cell_width * 0.28))
                height = max(int(width * 9 / 16), 1)
                thumb_x = cell_x + (cell_width - width) // 2
                thumb_y = y + (thumb_height - height) // 2
                try:
                    canvas.paste(
                        fit_thumbnail(video["thumbnail"], width, height),
                        (thumb_x, thumb_y),
                    )
                except Exception as exc:  # pragma: no cover - defensive
                    draw.rectangle(
                        [thumb_x, thumb_y, thumb_x + width, thumb_y + height],
                        fill=(200, 200, 200),
                    )
                    draw.text(
                        (thumb_x + 4, thumb_y + 4),
                        f"missing: {exc}",
                        fill=(80, 80, 80),
                        font=note_font,
                    )
                label = (
                    f"{video['date'].strftime('%m-%d')} · "
                    f"{human_views(video['views'])}"
                )
                label_width = draw.textlength(label, font=label_font)
                draw.text(
                    (cell_x + (cell_width - label_width) / 2, y + thumb_height + 3),
                    label,
                    fill=(70, 70, 70),
                    font=label_font,
                )
            y += thumb_height + label_height + 3
        y += block_gap

    footer = (
        "Cached public thumbnails · members-only uploads excluded · "
        "thumbnail size is presentation, not sentiment"
    )
    draw.text(
        (margin, total_height - margin + 2),
        footer,
        fill=(95, 95, 95),
        font=note_font,
    )

    save_canvas(canvas, output)
    print(
        f"wrote {output} ({canvas.width}x{canvas.height}, "
        f"{len(videos)} thumbnails, {len(channels)} channels)"
    )


def render_calendar(
    videos: list[dict],
    start: date,
    end: date,
    output: Path,
    title: str | None,
) -> None:
    """Render a compact 3-month calendar of the day's most-viewed upload."""
    if not videos:
        raise SystemExit("no cached videos found for the selected window")

    by_day: dict[date, list[dict]] = defaultdict(list)
    for video in videos:
        by_day[video["date"]].append(video)

    first_monday = start - timedelta(days=start.weekday())
    last_sunday = end + timedelta(days=6 - end.weekday())
    weeks = ((last_sunday - first_monday).days + 1) // 7

    margin = 22
    gap = 8
    cell_width = 190
    cell_height = 160
    weekday_height = 24
    header_height = 62
    footer_height = 34

    day_font = load_font(10, bold=True)
    weekday_font = load_font(10, bold=True)
    label_font = load_font(9)
    note_font = load_font(9)
    header_font = load_font(12, bold=True)
    title_font = load_font(21, bold=True)

    canvas_width = margin * 2 + 7 * cell_width + 6 * gap
    probe = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    title_lines = (
        wrap_text(probe, title, title_font, canvas_width - margin * 2) if title else []
    )
    top_banner = len(title_lines) * 27 + (8 if title_lines else 0)
    total_height = (
        margin * 2
        + top_banner
        + header_height
        + weekday_height
        + weeks * (cell_height + gap)
        + footer_height
    )
    canvas = Image.new("RGB", (canvas_width, total_height), (246, 246, 244))
    draw = ImageDraw.Draw(canvas)

    y = margin
    for line in title_lines:
        draw.text((margin, y), line, fill=(25, 25, 25), font=title_font)
        y += 27

    total_views = sum(v["views"] for v in videos)
    draw.text(
        (margin, y + 2),
        f"{start.isoformat()} → {end.isoformat()}   "
        f"{len(videos)} videos   {len(by_day)} upload days   "
        f"{human_views(total_views)} views",
        fill=(45, 45, 45),
        font=header_font,
    )
    draw.text(
        (margin, y + 24),
        "One cell per day · thumbnail is the day's most-viewed upload · "
        "shading follows total daily views",
        fill=(85, 85, 85),
        font=note_font,
    )
    y += header_height

    for column, name in enumerate(("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")):
        x = margin + column * (cell_width + gap)
        text_width = draw.textlength(name, font=weekday_font)
        draw.text(
            (x + (cell_width - text_width) / 2, y),
            name,
            fill=(70, 70, 70),
            font=weekday_font,
        )
    y += weekday_height

    max_day_views = max((sum(v["views"] for v in items) for items in by_day.values()), default=1) or 1
    cool = (205, 216, 230)
    warm = (250, 250, 248)
    for week in range(weeks):
        for column in range(7):
            day = first_monday + timedelta(days=week * 7 + column)
            x = margin + column * (cell_width + gap)
            cell_y = y + week * (cell_height + gap)
            if day < start or day > end:
                draw.rectangle(
                    [x, cell_y, x + cell_width, cell_y + cell_height],
                    fill=(240, 240, 238),
                    outline=(230, 230, 228),
                )
                continue

            items = by_day.get(day, [])
            day_views = sum(v["views"] for v in items)
            ratio = min(1.0, day_views / max_day_views)
            background = tuple(
                int(warm[i] + (cool[i] - warm[i]) * ratio) for i in range(3)
            )
            draw.rectangle(
                [x, cell_y, x + cell_width, cell_y + cell_height],
                fill=background,
                outline=(208, 210, 208),
            )
            draw.text(
                (x + 6, cell_y + 4),
                f"{day.strftime('%b')} {day.day}",
                fill=(35, 35, 35),
                font=day_font,
            )

            if not items:
                draw.text(
                    (x + cell_width / 2, cell_y + cell_height / 2 + 6),
                    "no uploads",
                    fill=(150, 150, 148),
                    font=note_font,
                    anchor="mm",
                )
                continue

            top = max(items, key=lambda v: v["views"])
            thumb_width = cell_width - 12
            thumb_height = int(thumb_width * 9 / 16)
            thumb_x = x + 6
            thumb_y = cell_y + 22
            try:
                canvas.paste(
                    fit_thumbnail(top["thumbnail"], thumb_width, thumb_height),
                    (thumb_x, thumb_y),
                )
            except Exception:  # pragma: no cover - defensive
                draw.rectangle(
                    [thumb_x, thumb_y, thumb_x + thumb_width, thumb_y + thumb_height],
                    fill=(205, 205, 205),
                )
            draw.text(
                (x + 6, thumb_y + thumb_height + 3),
                f"{len(items)} vids · {human_views(day_views)}",
                fill=(55, 55, 55),
                font=label_font,
            )
            channel = top["channel"]
            if draw.textlength(channel, font=note_font) > cell_width - 12:
                while channel and draw.textlength(channel + "…", font=note_font) > cell_width - 12:
                    channel = channel[:-1]
                channel = channel.rstrip() + "…"
            draw.text(
                (x + 6, thumb_y + thumb_height + 15),
                channel,
                fill=(95, 95, 95),
                font=note_font,
            )

    footer = (
        "Shading is total daily views, an attention proxy, not a sentiment score · "
        "members-only uploads excluded"
    )
    draw.text(
        (margin, total_height - margin + 2),
        footer,
        fill=(95, 95, 95),
        font=note_font,
    )

    save_canvas(canvas, output)
    print(
        f"wrote {output} ({canvas.width}x{canvas.height}, "
        f"{len(by_day)} days, {len(videos)} videos)"
    )


def render(
    videos_by_day: dict[date, list[dict]],
    days: list[date],
    sizing: str,
    base_width: int,
    output: Path,
    title: str | None,
) -> None:
    margin = 18
    gap = 10
    header_height = 62
    label_height = 22
    footer_height = 28

    column_widths, row_heights, _ = cell_geometry(
        videos_by_day, days, sizing, base_width
    )

    max_rows = max((len(videos_by_day[day]) for day in days), default=0)
    if max_rows == 0:
        raise SystemExit("no cached videos found for the selected dates")

    # Wide views are ordered oldest -> newest, matching the imported app's
    # timeline orientation. The newest day is on the right.
    ordered_days = sorted(days)
    total_width = margin * 2 + sum(column_widths[day] for day in ordered_days)
    total_width += gap * max(0, len(ordered_days) - 1)

    tallest_column = 0
    for day in ordered_days:
        height = len(videos_by_day[day]) * (row_heights[day] + label_height)
        tallest_column = max(tallest_column, height)

    canvas = Image.new("RGB", (total_width, 10), (246, 246, 244))
    draw = ImageDraw.Draw(canvas)
    title_font = load_font(20, bold=True)
    header_font = load_font(13, bold=True)
    subheader_font = load_font(11)
    footer_font = load_font(11)

    title_lines = (
        wrap_text(draw, title, title_font, total_width - margin * 2) if title else []
    )
    top_banner = len(title_lines) * 26 + (8 if title_lines else 0)

    total_height = (
        top_banner
        + header_height
        + tallest_column
        + footer_height
        + margin * 2
    )
    canvas = Image.new("RGB", (total_width, total_height), (246, 246, 244))
    draw = ImageDraw.Draw(canvas)

    y_text = margin
    for line in title_lines:
        draw.text((margin, y_text), line, fill=(25, 25, 25), font=title_font)
        y_text += 26

    x = margin
    y0 = margin + top_banner
    for day in ordered_days:
        column_width = column_widths[day]
        row_height = row_heights[day]
        videos = videos_by_day[day]
        day_total = sum(v["views"] for v in videos)
        draw.rectangle(
            [x, y0, x + column_width, y0 + header_height - 8],
            fill=(224, 226, 222),
        )
        draw.text(
            (x + 8, y0 + 8),
            day.isoformat(),
            fill=(35, 35, 35),
            font=header_font,
        )
        subheader = f"{len(videos)} videos · {human_views(day_total)} views"
        draw.text(
            (x + 8, y0 + 30),
            subheader,
            fill=(70, 70, 70),
            font=subheader_font,
        )

        cell_y = y0 + header_height
        for video in videos:
            width = column_width
            height = row_height
            if sizing in ("views-day", "views-all"):
                if sizing == "views-day":
                    peak = max(v["views"] for v in videos) or 1
                else:
                    peak = max(
                        (v["views"] for day_videos in videos_by_day.values() for v in day_videos),
                        default=1,
                    ) or 1
                # Linear scaling, with a floor so the smallest clip stays legible.
                ratio = max(0.28, min(1.0, video["views"] / peak))
                width = max(int(column_width * ratio), int(column_width * 0.28))
                height = max(int(width * 9 / 16), 1)

            thumb_x = x + (column_width - width) // 2
            try:
                image = fit_thumbnail(video["thumbnail"], width, height)
                canvas.paste(image, (thumb_x, cell_y))
            except Exception as exc:  # pragma: no cover - defensive
                draw.rectangle(
                    [thumb_x, cell_y, thumb_x + width, cell_y + height],
                    fill=(200, 200, 200),
                )
                draw.text(
                    (thumb_x + 4, cell_y + 4),
                    f"missing: {exc}",
                    fill=(80, 80, 80),
                    font=footer_font,
                )
            draw_label(
                draw,
                thumb_x,
                cell_y + height + 3,
                width,
                video["channel"],
                video["views"],
            )
            cell_y += row_height + label_height

        x += column_width + gap

    footer = (
        "Cached YouTube thumbnails · thumbnail size follows the selected rule · "
        "not a sentiment score"
    )
    draw.text(
        (margin, total_height - margin - 14),
        footer,
        fill=(95, 95, 95),
        font=footer_font,
    )

    save_canvas(canvas, output)
    print(f"wrote {output} ({canvas.width}x{canvas.height}, {sum(len(v) for v in videos_by_day.values())} thumbnails)")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--metadata-dir", type=Path, default=DEFAULT_METADATA)
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE)
    parser.add_argument(
        "--channels-file",
        type=Path,
        default=DEFAULT_CHANNELS,
        help="one channel name per line; # starts a comment",
    )
    parser.add_argument(
        "--exclude",
        default="",
        help="comma-separated channels to drop in addition to the fallback list",
    )
    parser.add_argument("--date", type=parse_date, help="single day, YYYY-MM-DD")
    parser.add_argument("--start", type=parse_date, help="first day, inclusive")
    parser.add_argument("--end", type=parse_date, help="last day, inclusive")
    parser.add_argument("--days", type=int, default=1, help="days ending at --date")
    parser.add_argument("--sizing", choices=SIZING_CHOICES, default="views-day")
    parser.add_argument(
        "--layout",
        choices=("columns", "timeline", "calendar"),
        default="columns",
        help="columns: one column per day; timeline: one block per channel; "
        "calendar: one cell per day",
    )
    parser.add_argument(
        "--per-row",
        type=int,
        default=12,
        help="timeline cells per row (default: 12)",
    )
    parser.add_argument("--base-width", type=int, default=240)
    parser.add_argument("--min-views", type=int, default=0)
    parser.add_argument("--limit", type=int, default=0, help="max videos per day")
    parser.add_argument(
        "--columns",
        type=int,
        default=0,
        help="single-day grid columns; default is a square-ish grid",
    )
    parser.add_argument("--title", default=None)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--manifest", type=Path, default=None)
    parser.add_argument(
        "--list-dates",
        action="store_true",
        help="print available dates and exit",
    )
    args = parser.parse_args(argv)

    include = read_channel_list(args.channels_file)
    exclude = set(FALLBACK_EXCLUDED)
    exclude.update(x.strip() for x in args.exclude.split(",") if x.strip())

    videos = load_videos(args.metadata_dir, args.cache_dir, include, exclude)
    if not videos:
        raise SystemExit("no videos with cached thumbnails found")

    by_date: dict[date, list[dict]] = defaultdict(list)
    for video in videos:
        by_date[video["date"]].append(video)

    if args.list_dates:
        for day in sorted(by_date):
            print(f"{day.isoformat()}\t{len(by_date[day])}")
        return 0

    if args.start or args.end:
        if not (args.start and args.end):
            raise SystemExit("--start and --end must be used together")
        start, end = args.start, args.end
    else:
        end = args.date or max(by_date)
        start = end - timedelta(days=max(1, args.days) - 1)

    days = [start + timedelta(days=i) for i in range((end - start).days + 1)]
    selected = {}
    for day in days:
        items = [v for v in by_date.get(day, []) if v["views"] >= args.min_views]
        items.sort(key=lambda v: v["views"], reverse=True)
        if args.limit:
            items = items[: args.limit]
        selected[day] = items

    if not any(selected.values()):
        raise SystemExit(
            f"no cached videos between {start} and {end} with views >= {args.min_views}"
        )

    base_width = max(120, args.base_width)
    all_selected = [video for day in days for video in selected[day]]
    if args.layout == "calendar":
        render_calendar(
            all_selected,
            start,
            end,
            args.output,
            args.title,
        )
    elif args.layout == "timeline":
        render_timeline(
            all_selected,
            start,
            end,
            args.sizing,
            base_width,
            args.per_row,
            args.output,
            args.title,
        )
    elif len(days) == 1:
        videos_for_day = selected[days[0]]
        columns = args.columns or max(1, math.ceil(math.sqrt(len(videos_for_day))))
        render_single_day(
            videos_for_day,
            days[0],
            args.sizing,
            base_width,
            columns,
            args.output,
            args.title,
        )
    else:
        render(
            selected,
            days,
            args.sizing,
            base_width,
            args.output,
            args.title,
        )

    manifest = args.manifest or args.output.with_suffix(".json")
    payload = {
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        "date_range": [start.isoformat(), end.isoformat()],
        "layout": args.layout,
        "per_row": args.per_row if args.layout == "timeline" else None,
        "sizing": None if args.layout == "calendar" else args.sizing,
        "min_views": args.min_views,
        "limit_per_day": args.limit,
        "channels_file": display_path(args.channels_file),
        "excluded": sorted(exclude),
        "output": display_path(args.output),
        "days": {
            day.isoformat(): [
                {
                    "channel": v["channel"],
                    "video_id": v["video_id"],
                    "views": v["views"],
                    "published_at": v["published_at"],
                    "title": v["title"],
                }
                for v in selected[day]
            ]
            for day in days
        },
    }
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {manifest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
