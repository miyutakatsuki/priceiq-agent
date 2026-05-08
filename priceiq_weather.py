"""PriceIQ Tool 4 — get_weather_signal (OpenWeather 5-day forecast).

Conditional invocation: only sports / garden categories trigger the live API
call. Other categories short-circuit to `applicable=False, multiplier=1.0`
without spending API quota — Planner v2 enforces this in its tool sequence.

Multiplier formula (clamped to [0.80, 1.15]):
  mult = 1.0 - 0.30 * rain_prob_5d
       + 0.05  if 20 ≤ avg_temp ≤ 28 (mild)
       - 0.10  if avg_temp < 15 or > 32 (extreme)

Sample: 5 BR cities (Sao Paulo / Rio / Brasilia / Salvador / Fortaleza) × 5 days
× 3-hour intervals = 200 forecast points averaged per call.

Graceful degradation: API failure → `degraded=True, multiplier=1.0`. Never raises.

Public API:
    get_weather_signal(category, region='BR', api_key=None) -> dict

Token (OPENWEATHER_API_KEY, 32-hex-char):
    Colab → userdata.get('OPENWEATHER_API_KEY')
    Local → export OPENWEATHER_API_KEY=...
    Explicit → get_weather_signal('sports', api_key=key)
"""

import os
import requests
from datetime import datetime, timezone

# Top-5 BR metros by Olist order volume — covers Southeast (SP, RJ),
# Center-West (Brasília), and Northeast (Salvador, Fortaleza). Together
# they account for roughly 70% of Olist's delivered orders. 5-city sample
# is a free-tier-friendly compromise (free OpenWeather quota = 60 calls/min;
# 5 cities × 1 query = 5 calls per agent invocation, well under).
_BR_CITIES = [
    ("Sao Paulo",  -23.5505, -46.6333),
    ("Rio",        -22.9068, -43.1729),
    ("Brasilia",   -15.7801, -47.9292),
    ("Salvador",   -12.9714, -38.5014),
    ("Fortaleza",   -3.7172, -38.5434),
]

# Only these categories are weather-sensitive (e-commerce purchase decisions
# correlate with outdoor weather). Both Olist Portuguese names and common
# English aliases accepted, so the Planner can use either form.
# Other categories (eletrônicos / cama_mesa_banho / etc.) short-circuit
# to applicable=False, weather_multiplier=1.0 — saves OpenWeather API quota.
_WEATHER_SENSITIVE = {
    "esporte_lazer", "ferramentas_jardim",
    "sports", "garden", "esporte", "jardim",
}

_API = "https://api.openweathermap.org/data/2.5/forecast"
_BR_AVG_TEMP = 24.0  # Brazil annual mean (°C) — averaging tropical NE coast (~27°C)
                     # with subtropical SE (~21°C). Used only for `temp_anomaly`
                     # field; multiplier itself uses absolute temp bands.


def get_weather_signal(category: str, region: str = "BR", api_key: str = None) -> dict:
    """返回天气信号 dict，含 weather_multiplier ∈ [0.80, 1.15]。

    非天气敏感品类返回 applicable=False, multiplier=1.0；
    API 失败返回 degraded=True, multiplier=1.0（不影响主流程）。
    """
    if category.lower() not in _WEATHER_SENSITIVE:
        return _neutral(category, region, applicable=False,
                        rationale=f"'{category}' not weather-sensitive")

    if region != "BR":
        return _neutral(category, region, degraded=True,
                        rationale="Only BR supported in MVP")

    key = api_key or os.environ.get("OPENWEATHER_API_KEY")
    if not key:
        return _neutral(category, region, degraded=True,
                        rationale="No API key provided")

    rain_probs, temps = [], []
    for name, lat, lon in _BR_CITIES:
        try:
            r = requests.get(_API, params={
                "lat": lat, "lon": lon, "appid": key,
                "units": "metric", "cnt": 40,  # 40 forecast points × 3h = 5-day horizon
            }, timeout=8)
            r.raise_for_status()
            for entry in r.json().get("list", []):
                rain_probs.append(entry.get("pop", 0.0))
                temps.append(entry["main"]["temp"])
        except (requests.RequestException, KeyError, ValueError):
            continue  # 单城市失败跳过

    if not temps:
        return _neutral(category, region, degraded=True,
                        rationale="All forecast queries failed")

    rain_prob = sum(rain_probs) / len(rain_probs)
    avg_temp = sum(temps) / len(temps)
    temp_anomaly = avg_temp - _BR_AVG_TEMP

    # ── Multiplier: start 1.0, rain pulls down, extreme temp pulls down, mild adds ──
    # Coefficients are heuristics (no calibration target available in scope).
    # Clamped to [0.80, 1.15] so weather alone can't dominate the elasticity signal.
    mult = 1.0 - rain_prob * 0.30          # up to -0.30 at 100% rain
    if 20 <= avg_temp <= 28:
        mult += 0.05                       # mild outdoor weather → slight boost
    elif avg_temp < 15 or avg_temp > 32:
        mult -= 0.10                       # too cold or too hot → discouraging
    mult = max(0.80, min(1.15, mult))

    return {
        "category": category,
        "region": region,
        "applicable": True,
        "cities_sampled": len(_BR_CITIES),
        "rain_prob_5d": round(rain_prob, 3),
        "avg_temp_5d_c": round(avg_temp, 2),
        "temp_anomaly": round(temp_anomaly, 2),
        "weather_multiplier": round(mult, 3),
        "rationale": _rationale(rain_prob, avg_temp, mult),
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "degraded": False,
    }


def _neutral(category, region, applicable=True, degraded=False, rationale=""):
    """非敏感品类 / 降级 → 返回中性 multiplier=1.0。"""
    return {
        "category": category, "region": region,
        "applicable": applicable, "degraded": degraded,
        "weather_multiplier": 1.0, "rationale": rationale,
    }


def _rationale(rain_prob, avg_temp, mult):
    """Compose a human-readable weather rationale string for the agent's answer."""
    rain = "high rain" if rain_prob > 0.5 else \
           "moderate rain" if rain_prob > 0.3 else "low rain"
    temp = "hot" if avg_temp > 30 else \
           "mild" if avg_temp > 20 else "cool"
    direction = "favorable" if mult > 1.02 else \
                "unfavorable" if mult < 0.95 else "neutral"
    return f"{rain}, {temp} — {direction} for outdoor categories"


if __name__ == "__main__":
    # 自测：key 从环境变量读，不进代码
    if not os.environ.get("OPENWEATHER_API_KEY"):
        print("⚠️  OPENWEATHER_API_KEY not set. Run:")
        print("    export OPENWEATHER_API_KEY=your_key && python priceiq_weather.py")
        exit(0)

    for cat in ["esporte_lazer", "ferramentas_jardim", "eletronicos"]:
        print(f"\n── {cat} ──")
        for k, v in get_weather_signal(cat).items():
            print(f"  {k}: {v}")
