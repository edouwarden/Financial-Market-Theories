#!/usr/bin/env python3
"""Fetch the free inputs for the weather-mood test.

Two sources, no API key:

* Open-Meteo historical archive, hourly reanalysis. The archive is free for
  non-commercial use and does not require a key.
* Yahoo Finance chart endpoint, daily bars. The endpoint is public but can rate
  limit; the script retries with a simple backoff.

The files are cached under data/raw/ and are gitignored. Re-running is cheap:
a file larger than 1 KB is left alone.

    python3 theories/18-weather-mood/scripts/collect_data.py
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
RAW = HERE.parent / "data" / "raw"

WEATHER_START = "1991-01-01"
WEATHER_END = "2026-11-06"
MARKET_START = 946684800  # 2000-01-01 UTC
MARKET_END = 1798761600  # 2027-01-01 UTC

CITIES = {
    "new_york": (40.7128, -74.0060, "America/New_York"),
    "denver": (39.7392, -104.9903, "America/Denver"),
    "london": (51.5074, -0.1278, "Europe/London"),
    "frankfurt": (50.1109, 8.6821, "Europe/Berlin"),
    "tokyo": (35.6762, 139.6503, "Asia/Tokyo"),
}

HOURLY = (
    "temperature_2m,apparent_temperature,precipitation,cloud_cover,"
    "weather_code,wind_speed_10m,wind_gusts_10m,relative_humidity_2m"
)

SYMBOLS = {
    "SPY": "SPY",
    "QQQ": "QQQ",
    "IWM": "IWM",
    "VIX": "^VIX",
    "FTSE": "^FTSE",
    "DAX": "^GDAXI",
    "NIKKEI": "^N225",
    "CL": "CL=F",
    "NG": "NG=F",
    "XLE": "XLE",
}


def fetch(url: str, destination: Path, attempts: int = 6) -> None:
    if destination.exists() and destination.stat().st_size > 1024:
        print(f"cached  {destination}  {destination.stat().st_size:,} bytes")
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    for attempt in range(1, attempts + 1):
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                payload = response.read()
            destination.write_bytes(payload)
            print(f"wrote   {destination}  {len(payload):,} bytes")
            return
        except urllib.error.HTTPError as error:
            if error.code != 429 or attempt == attempts:
                raise
            delay = 20 * attempt
            print(f"429 on {destination.name}; retrying in {delay}s")
            time.sleep(delay)
        except Exception as error:  # network hiccup
            if attempt == attempts:
                raise
            delay = 10 * attempt
            print(f"{type(error).__name__} on {destination.name}; retrying in {delay}s")
            time.sleep(delay)


def fetch_weather() -> None:
    for city, (latitude, longitude, timezone) in CITIES.items():
        query = urllib.parse.urlencode(
            {
                "latitude": latitude,
                "longitude": longitude,
                "start_date": WEATHER_START,
                "end_date": WEATHER_END,
                "hourly": HOURLY,
                "timezone": timezone,
            }
        )
        url = "https://archive-api.open-meteo.com/v1/archive?" + query
        fetch(url, RAW / f"openmeteo_{city}.json")
        time.sleep(8)


def fetch_markets() -> None:
    for name, symbol in SYMBOLS.items():
        encoded = urllib.parse.quote(symbol, safe="")
        url = (
            "https://query1.finance.yahoo.com/v8/finance/chart/"
            f"{encoded}?period1={MARKET_START}&period2={MARKET_END}"
            "&interval=1d&events=div%2Csplits&includeAdjustedClose=true"
        )
        fetch(url, RAW / f"yahoo_{name}.json")
        time.sleep(2)


def main() -> int:
    RAW.mkdir(parents=True, exist_ok=True)
    fetch_weather()
    fetch_markets()
    files = sorted(RAW.glob("*.json"))
    total = sum(path.stat().st_size for path in files)
    print(f"{len(files)} files, {total / 1e6:.1f} MB under {RAW}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
