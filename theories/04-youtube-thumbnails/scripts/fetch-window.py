#!/usr/bin/env python3
"""Fetch a date-bounded YouTube window for the thumbnail panel.

The imported app in ``test/`` used ``scrapetube`` and a Tkinter UI. This script
is the headless replacement: it reads ``data/channels.txt``, asks ``yt-dlp`` for
the channel's video tab, then resolves each candidate's exact upload date and
view count through YouTube's public InnerTube player endpoint.

Only public thumbnails and public metadata are stored. The script keeps a
delay (plus jitter) between requests, resumes per channel, reuses thumbnails
already in the cache, and skips members-only uploads because they have no
public view count.

Requirements
------------
    python3 -m pip install requests pillow yt-dlp

Examples
--------
    python3 scripts/fetch-window.py --start 2026-08-04 --end 2026-11-04
    python3 scripts/fetch-window.py --start 2026-08-04 --end 2026-11-04 \\
        --delay 1.0 --force

The output is intentionally separate from the imported 2024--2025 cache:

    test/youtube_metadata_window/<channel>_videos.json
    test/youtube_cache_window/<video_id>.jpg
    results/fetch_manifest.json
"""

from __future__ import annotations

import argparse
import io
import json
import random
import re
import subprocess
import sys
import time
import urllib.parse
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import requests
from PIL import Image

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parent
DEFAULT_CHANNELS = PROJECT / "data" / "channels.txt"
DEFAULT_ALIASES = PROJECT / "data" / "channel_aliases.json"
DEFAULT_METADATA = PROJECT / "test" / "youtube_metadata_window"
DEFAULT_CACHE = PROJECT / "test" / "youtube_cache_window"
DEFAULT_MANIFEST = PROJECT / "results" / "fetch_manifest.json"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)
CONSENT_COOKIE = ("SOCS", "CAI")
INNERTUBE_CLIENT = "WEB"


def display_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(PROJECT))
    except ValueError:
        return str(path)


def read_channels(path: Path) -> list[str]:
    if not path.exists():
        raise SystemExit(f"channel list not found: {path}")
    channels: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0].strip()
        if line:
            channels.append(line)
    return channels


def read_aliases(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"could not read aliases: {exc}") from exc
    if not isinstance(raw, dict):
        raise SystemExit("channel_aliases.json must be a JSON object")
    return {str(k): str(v) for k, v in raw.items()}


def make_session() -> requests.Session:
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": USER_AGENT,
            "Accept-Language": "en-US,en;q=0.9",
        }
    )
    session.cookies.set(CONSENT_COOKIE[0], CONSENT_COOKIE[1], domain=".youtube.com")
    return session


def politeness_sleep(delay: float) -> None:
    """Sleep for the nominal delay plus a little jitter.

    A fixed interval is easy to fingerprint and can look like a scraper. The
    jitter is deliberately small so a long run still finishes in minutes.
    """
    if delay > 0:
        time.sleep(delay + random.uniform(0.0, 0.2))


def request_json(
    session: requests.Session,
    method: str,
    url: str,
    *,
    delay: float,
    retries: int = 4,
    **kwargs: Any,
) -> dict[str, Any] | None:
    """Small retry wrapper so a transient 429 does not kill a long run.

    The delay is applied after every HTTP request, including successful ones.
    """
    for attempt in range(1, retries + 1):
        try:
            response = session.request(method, url, timeout=30, **kwargs)
        except requests.RequestException as exc:
            print(f"  request error ({attempt}/{retries}): {exc}", file=sys.stderr)
            politeness_sleep(delay)
            continue

        if response.status_code in (429, 500, 502, 503, 504):
            wait = min(60, 5 * attempt)
            print(
                f"  HTTP {response.status_code}; sleeping {wait}s",
                file=sys.stderr,
            )
            time.sleep(wait)
            continue
        if response.status_code >= 400:
            print(f"  HTTP {response.status_code}: {url}", file=sys.stderr)
            politeness_sleep(delay)
            return None
        try:
            payload = response.json()
        except ValueError:
            print(f"  non-JSON response: {url}", file=sys.stderr)
            politeness_sleep(delay)
            return None
        politeness_sleep(delay)
        return payload
    return None


def get_innertube_context(
    session: requests.Session, delay: float
) -> tuple[str, str, str | None]:
    """Return (api_key, client_version, visitor_data) from YouTube's page."""
    for url in (
        "https://www.youtube.com/?hl=en&gl=US",
        "https://www.youtube.com/@CoinBureau/videos?hl=en&gl=US",
    ):
        try:
            response = session.get(url, timeout=30)
        except requests.RequestException as exc:
            print(f"  context request failed: {exc}", file=sys.stderr)
            continue
        finally:
            politeness_sleep(delay)
        key = re.search(r'"INNERTUBE_API_KEY":"([^"]+)"', response.text)
        version = re.search(r'"INNERTUBE_CLIENT_VERSION":"([^"]+)"', response.text)
        visitor = re.search(r'"VISITOR_DATA":"([^"]+)"', response.text)
        if key and version:
            return (
                key.group(1),
                version.group(1),
                visitor.group(1) if visitor else None,
            )
    raise SystemExit("could not read YouTube InnerTube context")


def player_payload(
    video_id: str,
    client_version: str,
    *,
    visitor_data: str | None = None,
    client_name: str = INNERTUBE_CLIENT,
) -> dict[str, Any]:
    client: dict[str, Any] = {
        "clientName": client_name,
        "clientVersion": client_version,
        "hl": "en",
        "gl": "US",
    }
    if client_name == "ANDROID":
        client["androidSdkVersion"] = 30
    if visitor_data:
        client["visitorData"] = visitor_data
    return {"context": {"client": client}, "videoId": video_id}


def parse_upload_date(payload: dict[str, Any]) -> datetime | None:
    microformat = payload.get("microformat") or {}
    player_microformat = microformat.get("playerMicroformatRenderer") or {}
    for key in ("uploadDate", "publishDate", "releaseDate"):
        value = player_microformat.get(key)
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value)
            except ValueError:
                pass
    return None


def parse_watch_page(text: str) -> tuple[datetime | None, int | None, str | None]:
    """Pull the same fields from a watch page when the player call is gated."""
    uploaded = None
    match = re.search(r'"(?:uploadDate|publishDate)":"([^"]+)"', text)
    if match:
        try:
            uploaded = datetime.fromisoformat(match.group(1))
        except ValueError:
            pass
    views = None
    match = re.search(r'"viewCount":"(\d+)"', text)
    if match:
        views = int(match.group(1))
    title = None
    match = re.search(r'<meta property="og:title" content="([^"]+)"', text)
    if match:
        title = match.group(1)
    return uploaded, views, title


def fetch_watch_metadata(
    session: requests.Session,
    video_id: str,
    *,
    delay: float,
) -> tuple[datetime | None, int | None, str | None]:
    url = f"https://www.youtube.com/watch?v={video_id}&hl=en&gl=US&has_verified=1"
    for attempt in range(1, 3):
        try:
            response = session.get(url, timeout=30)
        except requests.RequestException as exc:
            print(f"  watch page error ({attempt}/2): {exc}", file=sys.stderr)
            politeness_sleep(delay)
            continue
        politeness_sleep(delay)
        if response.status_code >= 400:
            print(f"  watch page HTTP {response.status_code}: {video_id}", file=sys.stderr)
            continue
        uploaded, views, title = parse_watch_page(response.text)
        if uploaded is not None:
            return uploaded, views, title
    return None, None, None


def resolve_video(
    session: requests.Session,
    video_id: str,
    *,
    api_key: str,
    client_version: str,
    visitor_data: str | None,
    delay: float,
) -> tuple[datetime | None, int | None, str | None]:
    """Resolve exact date/views, with a watch-page fallback for bot gates."""
    player_url = f"https://www.youtube.com/youtubei/v1/player?key={api_key}"
    headers = {"Content-Type": "application/json"}
    if visitor_data:
        headers["X-Goog-Visitor-Id"] = visitor_data

    payload = request_json(
        session,
        "POST",
        player_url,
        delay=delay,
        json=player_payload(
            video_id,
            client_version,
            visitor_data=visitor_data,
        ),
        headers=headers,
    )
    if payload:
        uploaded = parse_upload_date(payload)
        if uploaded is not None:
            details = payload.get("videoDetails") or {}
            views = details.get("viewCount")
            try:
                view_count = int(views)
            except (TypeError, ValueError):
                view_count = None
            title = details.get("title")
            return uploaded, view_count, str(title) if title else None

    # A new visitor session is cheap; the previous one may have been flagged.
    uploaded, views, title = fetch_watch_metadata(
        session,
        video_id,
        delay=delay,
    )
    if uploaded is not None:
        return uploaded, views, title
    return None, None, None


def fetch_flat_listing(
    channel: str,
    channel_url: str,
    *,
    playlist_end: int,
    delay: float,
) -> list[dict[str, Any]]:
    """Use yt-dlp only for the video IDs and availability flags."""
    command = [
        sys.executable,
        "-m",
        "yt_dlp",
        "--flat-playlist",
        "--dump-json",
        "--no-warnings",
        "--ignore-errors",
        "--sleep-requests",
        str(delay),
        "--playlist-end",
        str(playlist_end),
        channel_url,
    ]
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=300,
            check=False,
        )
    except FileNotFoundError:
        raise SystemExit(
            "yt-dlp is not installed; run: python3 -m pip install yt-dlp"
        ) from None
    except subprocess.TimeoutExpired:
        print(f"  {channel}: yt-dlp timed out", file=sys.stderr)
        return []

    items: list[dict[str, Any]] = []
    for line in completed.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(item, dict) and item.get("id"):
            items.append(item)
    if completed.returncode != 0 and not items:
        message = completed.stderr.strip().splitlines()[-1] if completed.stderr else ""
        print(f"  {channel}: yt-dlp failed: {message}", file=sys.stderr)
    return items


def candidate_urls(channel: str, alias: str | None) -> list[str]:
    if alias:
        return [alias]
    quoted = urllib.parse.quote(channel)
    return [
        f"https://www.youtube.com/@{quoted}/videos",
        f"https://www.youtube.com/c/{quoted}/videos",
        f"https://www.youtube.com/user/{quoted}/videos",
    ]


def resolve_listing(
    channel: str,
    alias: str | None,
    *,
    playlist_end: int,
    delay: float,
) -> tuple[str, list[dict[str, Any]]]:
    for url in candidate_urls(channel, alias):
        items = fetch_flat_listing(
            channel,
            url,
            playlist_end=playlist_end,
            delay=delay,
        )
        if items:
            return url, items
    return "", []


def cached_thumbnail(cache_dir: Path, video_id: str) -> Path | None:
    for suffix in (".jpg", ".jpeg", ".png"):
        path = cache_dir / f"{video_id}{suffix}"
        if path.exists() and path.stat().st_size > 0:
            return path
    return None


def download_thumbnail(
    session: requests.Session,
    video_id: str,
    cache_dir: Path,
    *,
    delay: float,
) -> bool:
    if cached_thumbnail(cache_dir, video_id):
        return True
    target = cache_dir / f"{video_id}.jpg"
    for name in ("maxresdefault.jpg", "hqdefault.jpg"):
        url = f"https://i.ytimg.com/vi/{video_id}/{name}"
        try:
            response = session.get(url, timeout=30)
        except requests.RequestException as exc:
            print(f"  thumbnail error {video_id}: {exc}", file=sys.stderr)
            politeness_sleep(delay)
            continue
        if response.status_code == 200 and response.content:
            try:
                with Image.open(io.BytesIO(response.content)) as image:
                    image = image.convert("RGB")
                    # The renderer never needs more than 640 px wide. Storing a
                    # resized JPEG keeps a 1,000-video window around 40 MB.
                    image.thumbnail((640, 640), Image.Resampling.LANCZOS)
                    image.save(target, format="JPEG", quality=88, optimize=True)
                politeness_sleep(delay)
                return True
            except Exception as exc:  # pragma: no cover - defensive
                print(f"  thumbnail decode error {video_id}: {exc}", file=sys.stderr)
        politeness_sleep(delay)
    return False


def load_existing(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    return [item for item in raw if isinstance(item, dict)] if isinstance(raw, list) else []


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--channels-file", type=Path, default=DEFAULT_CHANNELS)
    parser.add_argument("--aliases-file", type=Path, default=DEFAULT_ALIASES)
    parser.add_argument("--metadata-dir", type=Path, default=DEFAULT_METADATA)
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--start", type=date.fromisoformat, required=True)
    parser.add_argument("--end", type=date.fromisoformat, required=True)
    parser.add_argument(
        "--delay",
        type=float,
        default=1.0,
        help="minimum seconds to wait after each HTTP request (default: 1.0; "
        "a small random jitter is added)",
    )
    parser.add_argument(
        "--playlist-end",
        type=int,
        default=300,
        help="max channel entries inspected before the date cutoff",
    )
    parser.add_argument(
        "--max-videos",
        type=int,
        default=400,
        help="safety cap on resolved videos per channel",
    )
    parser.add_argument(
        "--older-streak",
        type=int,
        default=4,
        help="stop after this many consecutive videos older than --start",
    )
    parser.add_argument("--only", default="", help="comma-separated channel names")
    parser.add_argument("--force", action="store_true", help="refetch channels already cached")
    parser.add_argument(
        "--no-thumbnails",
        action="store_true",
        help="resolve metadata only; reuse existing thumbnails",
    )
    args = parser.parse_args(argv)

    if args.end < args.start:
        raise SystemExit("--end must not be before --start")

    channels = read_channels(args.channels_file)
    if args.only:
        wanted = {x.strip() for x in args.only.split(",") if x.strip()}
        channels = [c for c in channels if c in wanted]
    aliases = read_aliases(args.aliases_file)
    args.metadata_dir.mkdir(parents=True, exist_ok=True)
    args.cache_dir.mkdir(parents=True, exist_ok=True)

    session = make_session()
    api_key, client_version, visitor_data = get_innertube_context(
        session,
        args.delay,
    )

    start_dt = datetime.combine(args.start, datetime.min.time(), tzinfo=timezone.utc)
    end_dt = datetime.combine(args.end + timedelta(days=1), datetime.min.time(), tzinfo=timezone.utc)
    start_ms = int(start_dt.timestamp() * 1000)
    end_ms = int(end_dt.timestamp() * 1000)

    summary: list[dict[str, Any]] = []
    total_kept = 0
    total_seen = 0
    total_skipped = 0
    started = time.time()

    for index, channel in enumerate(channels, start=1):
        metadata_path = args.metadata_dir / f"{channel}_videos.json"
        existing = load_existing(metadata_path)
        if existing and not args.force:
            in_window = [
                item
                for item in existing
                if isinstance(item.get("published_at"), (int, float))
                and start_ms <= int(item["published_at"]) < end_ms
            ]
            print(
                f"[{index:2d}/{len(channels)}] {channel}: cached "
                f"({len(in_window)} in window)"
            )
            summary.append(
                {
                    "channel": channel,
                    "status": "cached",
                    "videos": len(in_window),
                }
            )
            total_kept += len(in_window)
            continue

        alias = aliases.get(channel)
        listing_url, listing = resolve_listing(
            channel,
            alias,
            playlist_end=args.playlist_end,
            delay=args.delay,
        )
        if not listing:
            print(f"[{index:2d}/{len(channels)}] {channel}: no listing, skipped")
            summary.append({"channel": channel, "status": "no_listing", "videos": 0})
            continue

        kept: list[dict[str, Any]] = []
        older_streak = 0
        skipped_members = 0
        unresolved = 0
        channel_started = time.time()

        for item in listing:
            if len(kept) >= args.max_videos:
                break
            total_seen += 1
            video_id = str(item.get("id") or "")
            if not video_id:
                continue
            if item.get("availability") == "subscriber_only":
                skipped_members += 1
                total_skipped += 1
                continue

            uploaded, resolved_views, resolved_title = resolve_video(
                session,
                video_id,
                api_key=api_key,
                client_version=client_version,
                visitor_data=visitor_data,
                delay=args.delay,
            )
            if uploaded is None:
                unresolved += 1
                continue
            if uploaded.tzinfo is None:
                uploaded = uploaded.replace(tzinfo=timezone.utc)
            published_ms = int(uploaded.timestamp() * 1000)

            if published_ms < start_ms:
                older_streak += 1
                if older_streak >= args.older_streak:
                    break
                continue
            older_streak = 0
            if published_ms >= end_ms:
                # Premieres or scheduled uploads; keep scanning.
                continue

            if resolved_views is not None:
                views = int(resolved_views)
            else:
                views = int(item.get("view_count") or 0)

            title = resolved_title or item.get("title") or ""
            if isinstance(title, dict):
                runs = title.get("runs") or []
                title = runs[0].get("text", "") if runs else ""

            thumbnail_url = f"https://i.ytimg.com/vi/{video_id}/maxresdefault.jpg"
            if not args.no_thumbnails:
                if not download_thumbnail(
                    session,
                    video_id,
                    args.cache_dir,
                    delay=args.delay,
                ):
                    # Keep the metadata only if a usable cache entry exists.
                    if not cached_thumbnail(args.cache_dir, video_id):
                        unresolved += 1
                        continue

            kept.append(
                {
                    "title": str(title),
                    "thumbnail_url": thumbnail_url,
                    "published_at": published_ms,
                    "video_id": video_id,
                    "view_count": views,
                }
            )

        kept.sort(key=lambda item: item.get("published_at", 0), reverse=True)
        write_json(metadata_path, kept)
        total_kept += len(kept)
        elapsed = time.time() - channel_started
        print(
            f"[{index:2d}/{len(channels)}] {channel}: {len(kept)} in window "
            f"({skipped_members} members-only, {unresolved} unresolved) "
            f"{elapsed:.1f}s"
        )
        summary.append(
            {
                "channel": channel,
                "status": "fetched",
                "videos": len(kept),
                "members_only_skipped": skipped_members,
                "unresolved": unresolved,
                "listing_url": listing_url,
            }
        )

    manifest = {
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        "window": {"start": args.start.isoformat(), "end": args.end.isoformat()},
        "delay_seconds": args.delay,
        "channels_file": display_path(args.channels_file),
        "aliases_file": display_path(args.aliases_file),
        "metadata_dir": display_path(args.metadata_dir),
        "cache_dir": display_path(args.cache_dir),
        "channels_requested": len(channels),
        "entries_inspected": total_seen,
        "videos_in_window": total_kept,
        "members_only_skipped": total_skipped,
        "elapsed_seconds": round(time.time() - started, 1),
        "channels": summary,
    }
    write_json(args.manifest, manifest)
    print(
        f"\n{total_kept} videos in window across "
        f"{sum(1 for row in summary if row['videos'])} channels; "
        f"{total_seen} entries inspected, {total_skipped} members-only skipped."
    )
    print(f"wrote {args.manifest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
