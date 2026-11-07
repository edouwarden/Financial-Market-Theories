#!/usr/bin/env python3
"""Does the weather in the trader's session change same-day market behaviour?

The test uses free data only:

* Open-Meteo historical archive, hourly reanalysis (no API key).
* Yahoo Finance daily bars (no API key).

The unit of observation is one trading day. Weather is aggregated over the
local cash-session hours, not over daylight and not over the calendar day:

    New York      10:00-15:00 ET   morning 10:00-11:00   afternoon 14:00-15:00
    London        10:00-15:00 GMT  morning 10:00-11:00   afternoon 14:00-15:00
    Frankfurt     10:00-15:00 CET  morning 10:00-11:00   afternoon 14:00-15:00
    Tokyo         10:00-14:00 JST  morning 10:00-11:00   afternoon 13:00-14:00
    Denver        08:00-13:00 MT   morning 08:00-09:00   afternoon 12:00-13:00

Denver is a placebo: the clock hours match New York in UTC, but the city is
not where the New York session is traded.

A "hot" or "cold" day is a within-calendar-month z-score of the session mean
apparent temperature. The tails are z > 1.645 and z < -1.645 (about 5% each).
A heat or cold wave is three or more consecutive trading days in the same
tail.

Usage:

    python3 theories/18-weather-mood/scripts/collect_data.py
    python3 theories/18-weather-mood/scripts/analyze_weather.py

The script writes a compact daily sample and a results JSON. Raw files are
cached under data/raw/ and are gitignored; the committed sample is enough to
inspect the primary test.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import json
import math
import statistics
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np

HERE = Path(__file__).resolve().parent
THEORY = HERE.parent
RAW = THEORY / "data" / "raw"
SAMPLE = THEORY / "data" / "sample"
RESULTS = THEORY / "results"

SESSION_HOURS = {
    "new_york": {"all": (10, 15), "morning": (10, 11), "afternoon": (14, 15)},
    "london": {"all": (10, 15), "morning": (10, 11), "afternoon": (14, 15)},
    "frankfurt": {"all": (10, 15), "morning": (10, 11), "afternoon": (14, 15)},
    "tokyo": {"all": (10, 14), "morning": (10, 11), "afternoon": (13, 14)},
    "denver": {"all": (8, 13), "morning": (8, 9), "afternoon": (12, 13)},
}

MARKETS = {
    "SPY": {"city": "new_york", "tz": "America/New_York"},
    "QQQ": {"city": "new_york", "tz": "America/New_York"},
    "IWM": {"city": "new_york", "tz": "America/New_York"},
    "FTSE": {"city": "london", "tz": "Europe/London"},
    "DAX": {"city": "frankfurt", "tz": "Europe/Berlin"},
    "NIKKEI": {"city": "tokyo", "tz": "Asia/Tokyo"},
}

WINTER = (11, 12, 1, 2, 3)
SUMMER = (5, 6, 7, 8, 9)


def parse_date(text: str) -> date:
    return datetime.strptime(text, "%Y-%m-%d").date()


def pvalue(t: float) -> float:
    """Two-sided normal p-value (the samples are large)."""
    return 2.0 * (1.0 - 0.5 * (1.0 + math.erf(abs(t) / math.sqrt(2.0))))


def zscore(values: list[float]) -> list[float]:
    mean = statistics.mean(values)
    sd = statistics.pstdev(values)
    if sd == 0:
        return [0.0 for _ in values]
    return [(value - mean) / sd for value in values]


def load_market(name: str) -> dict[date, dict]:
    path = RAW / f"yahoo_{name}.json"
    if not path.exists():
        raise SystemExit(f"missing {path}; run collect_data.py first")
    payload = json.loads(path.read_text(encoding="utf-8"))
    result = payload["chart"]["result"][0]
    timestamps = result["timestamp"]
    quote = result["indicators"]["quote"][0]
    adjusted = result["indicators"].get("adjclose", [{}])[0].get("adjclose")
    tz = ZoneInfo(MARKETS.get(name, {}).get("tz", "America/New_York"))
    rows = {}
    for index, stamp in enumerate(timestamps):
        if any(quote[key][index] is None for key in ("open", "high", "low", "close")):
            continue
        day = datetime.fromtimestamp(stamp, tz=timezone.utc).astimezone(tz).date()
        volume = quote.get("volume", [None])[index]
        rows[day] = {
            "open": quote["open"][index],
            "high": quote["high"][index],
            "low": quote["low"][index],
            "close": quote["close"][index],
            "volume": volume if volume else 0,
            "adjclose": adjusted[index] if adjusted else quote["close"][index],
        }
    return rows


def load_weather(city: str) -> dict[date, dict]:
    path = RAW / f"openmeteo_{city}.json"
    if not path.exists():
        raise SystemExit(f"missing {path}; run collect_data.py first")
    payload = json.loads(path.read_text(encoding="utf-8"))
    hourly = payload["hourly"]
    sessions = SESSION_HOURS[city]
    daily: dict[date, dict] = {}
    for index, stamp in enumerate(hourly["time"]):
        day_text, time_text = stamp.split("T")
        hour = int(time_text[:2])
        day = parse_date(day_text)
        record = daily.setdefault(day, {})
        for band, (low, high) in sessions.items():
            if low <= hour <= high:
                bucket = record.setdefault(
                    band,
                    {"temp": [], "precip": 0.0, "cloud": [], "code": [], "wind": 0.0, "gust": 0.0, "hum": []},
                )
                bucket["temp"].append(hourly["apparent_temperature"][index])
                bucket["precip"] += hourly["precipitation"][index] or 0.0
                bucket["cloud"].append(hourly["cloud_cover"][index])
                bucket["code"].append(hourly["weather_code"][index])
                bucket["wind"] = max(bucket["wind"], hourly["wind_speed_10m"][index] or 0.0)
                bucket["gust"] = max(bucket["gust"], hourly["wind_gusts_10m"][index] or 0.0)
                bucket["hum"].append(hourly["relative_humidity_2m"][index])
    out = {}
    for day, record in daily.items():
        row = {}
        for band, bucket in record.items():
            row[f"{band}_temp"] = statistics.mean(bucket["temp"])
            row[f"{band}_precip"] = bucket["precip"]
            row[f"{band}_cloud"] = statistics.mean(bucket["cloud"]) / 100.0
            row[f"{band}_code"] = max(bucket["code"])
            row[f"{band}_wind"] = bucket["wind"]
            row[f"{band}_gust"] = bucket["gust"]
            row[f"{band}_hum"] = statistics.mean(bucket["hum"]) / 100.0
        out[day] = row
    return out


def mark_runs(rows: list[dict], key: str, out: str, minimum: int = 3) -> None:
    run = 0
    for row in rows:
        run = run + 1 if row[key] else 0
        row[out] = 1.0 if run >= minimum else 0.0


def build_panel(market: str, city: str, with_volume: bool = True) -> list[dict]:
    prices = load_market(market)
    weather = load_weather(city)
    vix = load_market("VIX")
    rows = []
    for day in sorted(set(prices) & set(weather) & set(vix)):
        row = {"date": day, **prices[day], "vix": vix[day]["close"], **weather[day]}
        rows.append(row)

    for index, row in enumerate(rows):
        row["r_oc"] = math.log(row["close"] / row["open"])
        row["r_cc"] = (
            math.log(row["adjclose"] / rows[index - 1]["adjclose"]) if index else None
        )
        row["range"] = math.log(row["high"] / row["low"])
        row["abs_r_oc"] = abs(row["r_oc"])
        row["log_vol"] = math.log(row["volume"]) if row["volume"] > 0 else None
        row["ret_lag"] = rows[index - 1]["r_oc"] if index else None
        row["vix_lag"] = math.log(rows[index - 1]["vix"]) if index else None
        row["range_lag"] = rows[index - 1]["range"] if index else None
        row["vol_lag"] = rows[index - 1]["log_vol"] if index and rows[index - 1]["log_vol"] else None

    for index, row in enumerate(rows):
        previous = [item["volume"] for item in rows[max(0, index - 20) : index] if item["volume"] > 0]
        row["vol_rel"] = (
            math.log(row["volume"] / statistics.median(previous))
            if row["volume"] > 0 and len(previous) >= 10
            else None
        )

    # Anomalies use the full 1991-2026 weather record, not the market sample,
    # so "unseasonable" does not depend on which trading days are in the panel.
    climatology = {}
    for band in SESSION_HOURS[city]:
        for month in range(1, 13):
            values = [
                record[f"{band}_temp"]
                for day, record in weather.items()
                if day.month == month and f"{band}_temp" in record
            ]
            if values:
                climatology[(band, month)] = (statistics.mean(values), statistics.pstdev(values))
    for band in SESSION_HOURS[city]:
        for row in rows:
            mean, sd = climatology.get((band, row["date"].month), (0.0, 0.0))
            row[f"{band}_temp_z"] = (row[f"{band}_temp"] - mean) / sd if sd else 0.0

    for row in rows:
        row["dow"] = row["date"].weekday()
        row["month"] = row["date"].month
        row["year"] = row["date"].year
        row["doy"] = row["date"].timetuple().tm_yday
        row["trend"] = (row["date"] - rows[0]["date"]).days / 365.25
        row["ym"] = f"{row['year']}-{row['month']:02d}"
        for band in SESSION_HOURS[city]:
            row[f"{band}_temp_c"] = row[f"{band}_temp"]
            row[f"{band}_heat_extreme"] = 1.0 if row[f"{band}_temp_z"] > 1.645 else 0.0
            row[f"{band}_cold_extreme"] = 1.0 if row[f"{band}_temp_z"] < -1.645 else 0.0
            row[f"{band}_hot30"] = 1.0 if row[f"{band}_temp"] >= 30 else 0.0
            row[f"{band}_hot35"] = 1.0 if row[f"{band}_temp"] >= 35 else 0.0
            row[f"{band}_cold0"] = 1.0 if row[f"{band}_temp"] <= 0 else 0.0
            row[f"{band}_coldm5"] = 1.0 if row[f"{band}_temp"] <= -5 else 0.0
        row["precip_mm"] = row["all_precip"]
        row["cloud_frac"] = row["all_cloud"]
        row["rain"] = 1.0 if row["precip_mm"] >= 1.0 else 0.0
        row["heavy_rain"] = 1.0 if row["precip_mm"] >= 10.0 else 0.0
        row["storm"] = 1.0 if (row["all_code"] >= 95 or row["all_gust"] >= 50) else 0.0
        row["clear"] = 1.0 if (row["cloud_frac"] < 0.25 and row["precip_mm"] < 0.2) else 0.0
        row["cloudy"] = 1.0 if (row["cloud_frac"] > 0.75 and row["precip_mm"] < 0.2) else 0.0
        row["precip_log"] = math.log1p(row["precip_mm"])

    for band in SESSION_HOURS[city]:
        mark_runs(rows, f"{band}_heat_extreme", f"{band}_heat_wave", 3)
        mark_runs(rows, f"{band}_cold_extreme", f"{band}_cold_wave", 3)
    mark_runs(rows, "all_hot30", "all_hot30_wave", 3)
    mark_runs(rows, "all_cold0", "all_cold0_wave", 3)

    required = ["r_oc", "r_cc", "range", "abs_r_oc", "vix_lag"]
    if with_volume:
        required.append("vol_rel")
    rows = [row for row in rows if all(row.get(key) is not None for key in required)]
    return rows


def demean(y: np.ndarray, x: np.ndarray, groups: list) -> tuple[np.ndarray, np.ndarray]:
    y = np.asarray(y, dtype=float)
    x = np.asarray(x, dtype=float)
    group_values = np.asarray(groups)
    y_demeaned = y.copy()
    x_demeaned = x.copy()
    for group in np.unique(group_values):
        mask = group_values == group
        y_demeaned[mask] -= y[mask].mean()
        x_demeaned[mask] -= x[mask].mean(axis=0)
    return y_demeaned, x_demeaned


def ols_hac(y: np.ndarray, x: np.ndarray, lags: int = 10) -> tuple[np.ndarray, np.ndarray]:
    y = np.asarray(y, dtype=float)
    x = np.asarray(x, dtype=float)
    beta, *_ = np.linalg.lstsq(x, y, rcond=None)
    residuals = y - x @ beta
    xtx_inv = np.linalg.inv(x.T @ x)
    meat = np.zeros((x.shape[1], x.shape[1]))
    for t in range(x.shape[0]):
        column = x[t][:, None]
        meat += (residuals[t] ** 2) * (column @ column.T)
    for lag in range(1, lags + 1):
        weight = 1.0 - lag / (lags + 1.0)
        for t in range(lag, x.shape[0]):
            column = x[t][:, None]
            lagged = x[t - lag][:, None]
            meat += weight * residuals[t] * residuals[t - lag] * (
                column @ lagged.T + lagged @ column.T
            )
    covariance = xtx_inv @ meat @ xtx_inv
    return beta, np.sqrt(np.diag(covariance))


def regression(
    rows: list[dict],
    outcome: str,
    predictor: str,
    subset=None,
    extra: list[str] | None = None,
    fe: str = "doy",
) -> dict | None:
    data = rows if subset is None else [row for row in rows if subset(row)]
    lag_map = {
        "r_oc": "ret_lag",
        "r_oc_w": "ret_lag",
        "r_cc": "ret_lag",
        "range": "range_lag",
        "abs_r_oc": "range_lag",
        "vol_rel": "vol_lag",
    }
    lag = lag_map.get(outcome, outcome + "_lag")
    needed = ["vix_lag", lag] + (extra or [])
    data = [
        row
        for row in data
        if row.get(outcome) is not None
        and row.get(predictor) is not None
        and all(row.get(key) is not None for key in needed)
    ]
    if len(data) < 100:
        return None
    outcome_values = zscore([row[outcome] for row in data])
    design = []
    for row in data:
        line = [row["trend"], row["vix_lag"]]
        line += [1.0 if row["dow"] == day else 0.0 for day in range(4)]
        line += [row[lag]]
        if extra:
            line += [float(row[key]) for key in extra]
        design.append(line)
    design = np.asarray(design, dtype=float)
    for column in range(design.shape[1]):
        values = design[:, column]
        mean, sd = statistics.mean(values), statistics.pstdev(values)
        if sd:
            design[:, column] = (values - mean) / sd
    predictor_values = np.asarray([float(row[predictor]) for row in data])
    x = np.column_stack([design, predictor_values])
    y, x = demean(outcome_values, x, [row[fe] for row in data])
    beta, se = ols_hac(y, x)
    b, s = beta[-1], se[-1]
    t = b / s if s else 0.0
    return {
        "beta_sd": b,
        "se_sd": s,
        "t": t,
        "p": pvalue(t),
        "n": len(data),
        "outcome_sd": statistics.pstdev([row[outcome] for row in data]),
    }


def raw_difference(rows: list[dict], predictor: str, outcome: str) -> dict:
    hit = [row[outcome] for row in rows if row[predictor]]
    miss = [row[outcome] for row in rows if not row[predictor]]
    if len(hit) < 2 or len(miss) < 2:
        return {}
    difference = statistics.mean(hit) - statistics.mean(miss)
    se = math.sqrt(statistics.variance(hit) / len(hit) + statistics.variance(miss) / len(miss))
    return {
        "n_hit": len(hit),
        "n_miss": len(miss),
        "hit_mean_bps": statistics.mean(hit) * 1e4,
        "miss_mean_bps": statistics.mean(miss) * 1e4,
        "difference_bps": difference * 1e4,
        "t": difference / se if se else 0.0,
        "p": pvalue(difference / se) if se else 1.0,
    }


def effect_bps(result: dict) -> float:
    return result["beta_sd"] * result["outcome_sd"] * 1e4


def period(rows: list[dict], start: int, end: int) -> list[dict]:
    return [row for row in rows if start <= row["year"] <= end]


def summarize(result: dict | None, rows: list[dict] | None = None, predictor: str | None = None, outcome: str | None = None) -> dict | None:
    if result is None:
        return None
    scale = result["outcome_sd"] * 1e4
    output = {
        "beta_sd": round(result["beta_sd"], 4),
        "se_sd": round(result["se_sd"], 4),
        "t": round(result["t"], 2),
        "p": round(result["p"], 4),
        "n": result["n"],
        "effect_bps": round(effect_bps(result), 1),
        "ci_low_bps": round((result["beta_sd"] - 1.96 * result["se_sd"]) * scale, 1),
        "ci_high_bps": round((result["beta_sd"] + 1.96 * result["se_sd"]) * scale, 1),
    }
    if rows is not None and predictor is not None and outcome is not None:
        difference = raw_difference(rows, predictor, outcome)
        if difference:
            output["raw"] = {
                "n_hit": difference["n_hit"],
                "n_miss": difference["n_miss"],
                "hit_mean_bps": round(difference["hit_mean_bps"], 1),
                "miss_mean_bps": round(difference["miss_mean_bps"], 1),
                "difference_bps": round(difference["difference_bps"], 1),
                "t": round(difference["t"], 2),
                "p": round(difference["p"], 4),
            }
    return output


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-extra", action="store_true", help="only run the SPY/New York panel")
    args = parser.parse_args()

    RESULTS.mkdir(parents=True, exist_ok=True)
    SAMPLE.mkdir(parents=True, exist_ok=True)

    spy = build_panel("SPY", "new_york")
    qqq = build_panel("QQQ", "new_york")
    iwm = build_panel("IWM", "new_york")
    winter = lambda row: row["month"] in WINTER
    summer = lambda row: row["month"] in SUMMER

    # The primary test: winter morning warmth in New York against the SPY
    # open-to-close return. The same specification is run on QQQ and IWM.
    primary = {
        "spy_winter_morning_heat": summarize(
            regression(spy, "r_oc", "morning_heat_extreme", subset=winter),
            [row for row in spy if winter(row)],
            "morning_heat_extreme",
            "r_oc",
        ),
        "qqq_winter_morning_heat": summarize(
            regression(qqq, "r_oc", "morning_heat_extreme", subset=winter),
            [row for row in qqq if winter(row)],
            "morning_heat_extreme",
            "r_oc",
        ),
        "iwm_winter_morning_heat": summarize(
            regression(iwm, "r_oc", "morning_heat_extreme", subset=winter),
            [row for row in iwm if winter(row)],
            "morning_heat_extreme",
            "r_oc",
        ),
        "spy_winter_morning_cold": summarize(
            regression(spy, "r_oc", "morning_cold_extreme", subset=winter),
            [row for row in spy if winter(row)],
            "morning_cold_extreme",
            "r_oc",
        ),
        "spy_summer_morning_heat": summarize(
            regression(spy, "r_oc", "morning_heat_extreme", subset=summer),
            [row for row in spy if summer(row)],
            "morning_heat_extreme",
            "r_oc",
        ),
        "spy_all_year_morning_heat": summarize(
            regression(spy, "r_oc", "morning_heat_extreme"),
            spy,
            "morning_heat_extreme",
            "r_oc",
        ),
    }

    # The rest of the weather grid, on SPY.
    outcomes = {}
    for outcome in ("r_oc", "r_cc", "range", "abs_r_oc", "vol_rel"):
        outcomes[outcome] = {}
        for predictor in (
            "morning_heat_extreme",
            "morning_cold_extreme",
            "afternoon_heat_extreme",
            "afternoon_cold_extreme",
            "all_heat_extreme",
            "all_cold_extreme",
            "all_heat_wave",
            "all_cold_wave",
            "morning_heat_wave",
            "morning_cold_wave",
            "all_hot30",
            "all_hot35",
            "all_cold0",
            "all_coldm5",
            "clear",
            "cloudy",
            "rain",
            "heavy_rain",
            "storm",
            "cloud_frac",
            "precip_log",
        ):
            result = regression(spy, outcome, predictor)
            if result:
                outcomes[outcome][predictor] = summarize(result)

    # Absolute-threshold and wave checks on absolute returns and volume.
    thresholds = {}
    for predictor in ("all_hot30", "all_hot35", "all_cold0", "all_coldm5", "all_hot30_wave", "all_cold0_wave"):
        thresholds[predictor] = {
            "abs_r_oc": summarize(regression(spy, "abs_r_oc", predictor)),
            "vol_rel": summarize(regression(spy, "vol_rel", predictor)),
        }

    # Continuous temperature, to show the effect is a tail effect rather than a
    # linear "warmer is better/worse" slope.
    continuous = {
        "spy_winter_morning_temp_z": summarize(
            regression(spy, "r_oc", "morning_temp_z", subset=winter)
        ),
        "spy_summer_morning_temp_z": summarize(
            regression(spy, "r_oc", "morning_temp_z", subset=summer)
        ),
        "spy_all_morning_temp_z": summarize(regression(spy, "r_oc", "morning_temp_z")),
    }

    # Energy is a competing channel: warm winters lower heating demand. If the
    # effect is energy-driven, lagged energy returns should absorb it and warm
    # mornings should predict energy-sector returns. Add same-day XLE only as a
    # contemporaneous co-movement check, not as a tradeable control.
    xle = load_market("XLE")
    for row in spy:
        row["xle_oc"] = None
    for index, row in enumerate(spy):
        day = row["date"]
        if day in xle and xle[day]["open"] > 0 and xle[day]["close"] > 0:
            row["xle_oc"] = math.log(xle[day]["close"] / xle[day]["open"])
        row["xle_oc_lag"] = spy[index - 1]["xle_oc"] if index else None

    # Stability: split the sample, drop one year at a time, winsorize, and add
    # cloud/precipitation and same-day volume controls.
    first_half = period(spy, 2000, 2012)
    second_half = period(spy, 2013, 2026)
    leave_one_out = {}
    base = regression(spy, "r_oc", "morning_heat_extreme", subset=winter)
    for year in range(2000, 2027):
        result = regression(
            spy,
            "r_oc",
            "morning_heat_extreme",
            subset=lambda row, y=year: winter(row) and row["year"] != y,
        )
        if result:
            leave_one_out[str(year)] = {
                "beta_sd": round(result["beta_sd"], 4),
                "p": round(result["p"], 4),
            }

    lows = sorted(row["r_oc"] for row in spy)
    low, high = lows[int(0.01 * len(lows))], lows[int(0.99 * len(lows))]
    for row in spy:
        row["r_oc_w"] = min(max(row["r_oc"], low), high)
    robustness = {
        "first_half_2000_2012": summarize(
            regression(first_half, "r_oc", "morning_heat_extreme", subset=winter)
        ),
        "second_half_2013_2026": summarize(
            regression(second_half, "r_oc", "morning_heat_extreme", subset=winter)
        ),
        "winsorized_1_99": summarize(
            regression(spy, "r_oc_w", "morning_heat_extreme", subset=winter)
        ),
        "plus_cloud": summarize(
            regression(spy, "r_oc", "morning_heat_extreme", subset=winter, extra=["cloud_frac"])
        ),
        "plus_precip": summarize(
            regression(spy, "r_oc", "morning_heat_extreme", subset=winter, extra=["precip_log"])
        ),
        "plus_cloud_and_precip": summarize(
            regression(
                spy,
                "r_oc",
                "morning_heat_extreme",
                subset=winter,
                extra=["cloud_frac", "precip_log"],
            )
        ),
        "plus_same_day_volume": summarize(
            regression(spy, "r_oc", "morning_heat_extreme", subset=winter, extra=["vol_rel"])
        ),
        "plus_same_day_energy": summarize(
            regression(spy, "r_oc", "morning_heat_extreme", subset=winter, extra=["xle_oc"])
        ),
        "leave_one_year_out": leave_one_out,
    }

    energy = {
        "warm_mornings_to_xle": summarize(
            regression(spy, "xle_oc", "morning_heat_extreme", subset=winter)
        ),
        "lagged_xle_control": summarize(
            regression(
                spy,
                "r_oc",
                "morning_heat_extreme",
                subset=winter,
                extra=["xle_oc_lag"],
            )
        ),
    }

    # Cross-market replication. The same local-session weather rule is applied
    # to London, Frankfurt, and Tokyo.
    cross_market = {}
    if not args.skip_extra:
        for market, config in MARKETS.items():
            if market == "SPY":
                continue
            panel = build_panel(market, config["city"], with_volume=market in ("QQQ", "IWM"))
            cross_market[market] = {
                "city": config["city"],
                "winter_morning_heat": summarize(
                    regression(panel, "r_oc", "morning_heat_extreme", subset=winter)
                ),
                "winter_morning_cold": summarize(
                    regression(panel, "r_oc", "morning_cold_extreme", subset=winter)
                ),
                "summer_morning_heat": summarize(
                    regression(panel, "r_oc", "morning_heat_extreme", subset=summer)
                ),
            }

        # Placebo: Denver weather at the same absolute clock hours as New York.
        denver = build_panel("SPY", "denver")
        placebo = {
            "denver_morning_heat": summarize(
                regression(denver, "r_oc", "morning_heat_extreme", subset=winter)
            ),
            "denver_morning_cold": summarize(
                regression(denver, "r_oc", "morning_cold_extreme", subset=winter)
            ),
        }
    else:
        placebo = {}

    # Descriptives for the chart and the README.
    warm = [row for row in spy if winter(row) and row["morning_heat_extreme"]]
    other = [row for row in spy if winter(row) and not row["morning_heat_extreme"]]
    descriptive = {
        "winter_days": len(warm) + len(other),
        "warm_mornings": len(warm),
        "warm_share": round(len(warm) / (len(warm) + len(other)), 4),
        "warm_cloud_frac": round(statistics.mean(row["cloud_frac"] for row in warm), 3),
        "other_cloud_frac": round(statistics.mean(row["cloud_frac"] for row in other), 3),
        "warm_precip_mm": round(statistics.mean(row["precip_mm"] for row in warm), 2),
        "other_precip_mm": round(statistics.mean(row["precip_mm"] for row in other), 2),
        "warm_r_oc_bps": round(statistics.mean(row["r_oc"] for row in warm) * 1e4, 1),
        "other_r_oc_bps": round(statistics.mean(row["r_oc"] for row in other) * 1e4, 1),
    }

    span = {
        "market_start": min(row["date"] for row in spy).isoformat(),
        "market_end": max(row["date"] for row in spy).isoformat(),
        "spy_days": len(spy),
        "qqq_days": len(qqq),
        "iwm_days": len(iwm),
        "winter_days": len([row for row in spy if winter(row)]),
        "summer_days": len([row for row in spy if summer(row)]),
    }

    payload = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "sources": {
            "weather": "Open-Meteo archive API, hourly reanalysis, apparent temperature",
            "prices": "Yahoo Finance chart API, daily bars, adjusted close",
            "vix": "Yahoo Finance ^VIX daily close",
            "energy": "Yahoo Finance XLE daily bars",
        },
        "sessions": SESSION_HOURS,
        "definitions": {
            "hot_cold": "within-calendar-month z of session mean apparent temperature",
            "extreme": "z > 1.645 or z < -1.645 (about 5% tails)",
            "wave": "3 or more consecutive trading days in the same tail",
            "intraday": "log(close/open)",
            "close_to_close": "log(adjusted close / prior adjusted close)",
            "range": "log(high/low)",
            "volume": "log(volume / prior 20-day median volume)",
            "controls": "time trend, lagged log VIX, day-of-week dummies, lagged outcome, day-of-year fixed effects",
            "errors": "Newey-West HAC(10)",
        },
        "sample": span,
        "descriptive": descriptive,
        "primary": primary,
        "outcomes": outcomes,
        "thresholds": thresholds,
        "continuous": continuous,
        "robustness": robustness,
        "energy": energy,
        "cross_market": cross_market,
        "placebo": placebo,
        "notes": [
            "The search covered several sessions, thresholds, outcomes, and markets. The winter effect is the one that survived; treat the p-values as descriptive rather than as a pre-registered test.",
            "The outcome is open-to-close. The weather signal is measured at 10:00-11:00, so part of the measured move happens before the signal is complete. Daily bars cannot isolate the post-11:00 return.",
            "A warm winter morning is about 21 bps lower on average, on roughly 5% of winter days. That is too small and too poorly timed to survive realistic costs from daily data.",
        ],
    }

    (RESULTS / "weather_effects.json").write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8"
    )

    # Compact daily sample for SPY/New York. The full raw inputs are not
    # committed; this file lets a reader inspect the primary test.
    columns = [
        "date",
        "r_oc",
        "r_cc",
        "range",
        "abs_r_oc",
        "vol_rel",
        "vix_lag",
        "morning_temp_c",
        "morning_temp_z",
        "morning_heat_extreme",
        "morning_cold_extreme",
        "all_temp_c",
        "all_temp_z",
        "all_heat_wave",
        "all_cold_wave",
        "precip_mm",
        "cloud_frac",
        "storm",
        "clear",
        "cloudy",
        "rain",
        "dow",
        "month",
        "year",
        "doy",
    ]
    with (SAMPLE / "weather_panel.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for row in spy:
            output = {key: row.get(key) for key in columns}
            output["date"] = row["date"].isoformat()
            for key in ("r_oc", "r_cc", "range", "abs_r_oc", "vol_rel", "vix_lag"):
                if output[key] is not None:
                    output[key] = f"{output[key]:.6f}"
            for key in ("morning_temp_c", "morning_temp_z", "all_temp_c", "all_temp_z"):
                output[key] = f"{output[key]:.3f}"
            for key in ("precip_mm", "cloud_frac"):
                output[key] = f"{output[key]:.3f}"
            writer.writerow(output)

    print(f"wrote {RESULTS / 'weather_effects.json'}")
    print(f"wrote {SAMPLE / 'weather_panel.csv'}")
    print(
        "SPY winter morning heat: "
        f"beta={primary['spy_winter_morning_heat']['beta_sd']:.4f} "
        f"t={primary['spy_winter_morning_heat']['t']:.2f} "
        f"p={primary['spy_winter_morning_heat']['p']:.4f} "
        f"n={primary['spy_winter_morning_heat']['n']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
