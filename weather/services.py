from __future__ import annotations

import io
from datetime import datetime, timedelta, timezone
from typing import List, Tuple

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd
import requests
from dateutil import parser as date_parser


PRIMARY_OPEN_METEO_URL = "https://api.open-meteo.com/v1/meteoswiss"
FALLBACK_OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"


def build_primary_params(latitude: float, longitude: float) -> dict:
    # Requirements: use the MeteoSwiss endpoint and past 2 days
    return {
        "latitude": latitude,
        "longitude": longitude,
        "hourly": "temperature_2m,relative_humidity_2m",
        "past_days": 2,
        "timezone": "UTC",
    }


def build_fallback_params(latitude: float, longitude: float) -> dict:
    # Fallback using forecast endpoint with past 48 hours
    return {
        "latitude": latitude,
        "longitude": longitude,
        "hourly": "temperature_2m,relative_humidity_2m",
        "past_hours": 48,
        "timezone": "UTC",
    }


def fetch_weather_series(latitude: float, longitude: float) -> pd.DataFrame:
    # Try MeteoSwiss endpoint first per requirement
    params = build_primary_params(latitude, longitude)
    resp = requests.get(PRIMARY_OPEN_METEO_URL, params=params, timeout=30)
    if not resp.ok:
        # fallback to forecast endpoint if MeteoSwiss is unavailable in region
        params = build_fallback_params(latitude, longitude)
        resp = requests.get(FALLBACK_OPEN_METEO_URL, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    times = data["hourly"]["time"]
    temps = data["hourly"]["temperature_2m"]
    hums = data["hourly"]["relative_humidity_2m"]

    df = pd.DataFrame(
        {
            "timestamp": [date_parser.isoparse(t) for t in times],
            "temperature_2m": pd.to_numeric(temps, errors="coerce"),
            "relative_humidity_2m": pd.to_numeric(hums, errors="coerce"),
        }
    )
    # Remove any rows with missing values to avoid NaT/NaN issues when casting
    df = df.dropna(subset=["timestamp", "temperature_2m", "relative_humidity_2m"])
    df.sort_values("timestamp", inplace=True)
    return df


def render_chart_png(df: pd.DataFrame) -> bytes:
    fig, ax1 = plt.subplots(figsize=(10, 4))
    ax2 = ax1.twinx()

    ax1.plot(df["timestamp"], df["temperature_2m"], color="tab:red", label="Temperature (°C)")
    ax2.plot(df["timestamp"], df["relative_humidity_2m"], color="tab:blue", label="Humidity (%)")

    ax1.set_xlabel("Time (UTC)")
    ax1.set_ylabel("Temperature (°C)", color="tab:red")
    ax2.set_ylabel("Humidity (%)", color="tab:blue")
    ax1.grid(True, linestyle=":", alpha=0.5)

    fig.autofmt_xdate()
    fig.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=160, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf.read()


def pdf_html_template(location: str, start: datetime, end: datetime, base64_png: str) -> str:
    return f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset='utf-8'>
  <title>Weather Report</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 24px; }}
    h1 {{ margin-bottom: 4px; }}
    .meta {{ color: #555; margin-bottom: 16px; }}
    img {{ width: 100%; height: auto; }}
    table {{ border-collapse: collapse; width: 100%; margin-top: 12px; }}
    th, td {{ border: 1px solid #ddd; padding: 6px 8px; font-size: 12px; }}
    th {{ background: #f5f5f5; }}
  </style>
  </head>
  <body>
    <h1>Weather Report</h1>
    <div class="meta">Location: {location}<br/>Range: {start} to {end} (UTC)</div>
    <img src="data:image/png;base64,{base64_png}" />
  </body>
</html>
"""


