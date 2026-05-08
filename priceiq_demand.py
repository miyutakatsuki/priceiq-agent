"""PriceIQ Tool 3 — get_demand_signals (BR holidays + Olist seasonality).

Formula (response to instructor comment #2):
    demand_multiplier = α_h * holiday_mult + α_s * seasonality_mult
    default α_h=0.4, α_s=0.6  (long-run seasonality weighted higher)

Holiday: 8 Brazilian holidays ±14 days, exponential decay (half-life 7 days).
Seasonality: month_avg / annual_avg from Olist delivered orders.

Public API:
    get_demand_signals(category, country='BR', today=None) -> dict
        Returns demand_multiplier + holiday + seasonality + sensitivity_analysis
        across α_h ∈ {0.2, 0.4, 0.6}.

Why not pytrends: unstable on Colab + multipliers were not interpretable
(instructor critique #2). Replaced with explicit α-weighted formula.
"""

import sqlite3
from datetime import date
from typing import Optional


# ── 巴西节假日 + 经验性影响倍数 ──────────────────────────────
# raw_impact: 该日期对 e-commerce 销量的相对影响（基于 Olist 数据观察）
# Hardcoded for 2026 (the submission year). For 2027+ regenerate dates from a
# BR holiday calendar source; impacts are stable. Phase 4 todo if course extends.
_BR_HOLIDAYS_2026 = [
    ("Carnival",        date(2026,  2, 17), -0.20),
    ("Easter",          date(2026,  4,  5), +0.10),
    ("Mothers Day",     date(2026,  5, 10), +0.15),
    ("Valentines BR",   date(2026,  6, 12), +0.15),
    ("Fathers Day",     date(2026,  8,  9), +0.10),
    ("Childrens Day",   date(2026, 10, 12), +0.25),  # major BR gift-giving holiday
    ("Black Friday",    date(2026, 11, 27), +0.30),
    ("Christmas",       date(2026, 12, 25), +0.30),
]

_HOLIDAY_RADIUS = 14   # ±14 days: covers consumer pre-shopping + post-clearance windows
_HOLIDAY_DECAY = 0.5   # 7-day half-life: matches typical promo cycle decay observed
                       # in retail panels (full strength on day, ~half a week out, ~quarter at radius edge)


def _holiday_signal(today: Optional[date] = None) -> dict:
    """返回距今最近节假日及其衰减后影响倍数。"""
    if today is None:
        today = date.today()

    nearest = None
    nearest_days = None
    raw = 0.0
    for name, d, impact in _BR_HOLIDAYS_2026:
        days = (d - today).days
        if -_HOLIDAY_RADIUS <= days <= _HOLIDAY_RADIUS:
            if nearest is None or abs(days) < abs(nearest_days):
                nearest, nearest_days, raw = name, days, impact

    if nearest is None:
        return {"nearest_holiday": None, "days_to_holiday": None,
                "holiday_multiplier": 1.0,
                "rationale": "No major BR holiday within +/-14 days"}

    decay = _HOLIDAY_DECAY ** (abs(nearest_days) / 7)
    mult = 1.0 + raw * decay
    # days_to_holiday: positive = future, negative = past, 0 = today
    when = (f"{nearest_days} days before {nearest}" if nearest_days > 0 else
            f"{abs(nearest_days)} days after {nearest}" if nearest_days < 0 else
            f"today is {nearest}")
    return {
        "nearest_holiday": nearest,
        "days_to_holiday": nearest_days,
        "holiday_multiplier": round(mult, 3),
        "rationale": f"{when} (raw impact {raw:+.0%}, decayed to {(mult-1)*100:+.1f}%)",
    }


def _seasonality_signal(category: str, ref_month: Optional[int] = None) -> dict:
    """品类的月度季节性 multiplier（month_avg / annual_avg）。"""
    if ref_month is None:
        ref_month = date.today().month

    # Reuse Tool 1's cached SQLite handle via priceiq_data._ensure_db
    from priceiq_data import _ensure_db
    with sqlite3.connect(_ensure_db()) as conn:
        # Aggregate delivered orders per calendar month (1-12) for this category.
        # Cross-year months are summed together (Jan 2017 + Jan 2018 = "month 1")
        # so the resulting pattern represents seasonal, not annual, variation.
        rows = conn.execute("""
            SELECT
                CAST(strftime('%m', o.order_purchase_timestamp) AS INTEGER) AS mo,
                COUNT(*) AS n
            FROM order_items oi
            JOIN orders o ON oi.order_id = o.order_id
            JOIN products p ON oi.product_id = p.product_id
            WHERE p.product_category_name = ?
              AND o.order_status = 'delivered'
            GROUP BY mo
            ORDER BY mo
        """, (category,)).fetchall()

    # Need ≥6 distinct months to give "seasonality" any meaning. Below that the
    # signal is dominated by single-month noise. Fall back to neutral 1.0.
    if len(rows) < 6:
        return {"seasonality_multiplier": 1.0, "monthly_pattern": {},
                "rationale": "Insufficient monthly data for seasonality"}

    # Multiplier = month_orders / mean_monthly_orders. 1.20 means this month
    # historically gets 20% more orders than the mean across observed months
    # (not strictly annual — sparse categories may miss some calendar months,
    # though the n<6 guard above filters out the most degenerate cases).
    # Months absent from `rows` (zero orders) get multiplier 1.0 via .get(),
    # which is conservative — they don't penalize the forecast.
    monthly = {mo: n for mo, n in rows}
    avg = sum(monthly.values()) / len(monthly)
    pattern = {mo: round(n / avg, 3) for mo, n in monthly.items()}
    mult = pattern.get(ref_month, 1.0)

    return {
        "seasonality_multiplier": mult,
        "ref_month": ref_month,
        "monthly_pattern": pattern,
        "n_months_observed": len(monthly),
        "rationale": (f"Month {ref_month} historically {(mult-1)*100:+.1f}% "
                      f"vs avg across {len(monthly)} observed months"),
    }


def get_demand_signals(category: str, country: str = "BR",
                       today: Optional[date] = None) -> dict:
    """组合 holiday + seasonality 给综合 demand multiplier。

    显式公式：
        demand_multiplier = α_h * holiday_mult + α_s * seasonality_mult
        默认 α_h = 0.4, α_s = 0.6（季节性长期更稳定，给更高权重）

    输出 sensitivity_analysis 字段，便于报告讨论权重选择。
    """
    if country != "BR":
        return {"category": category, "country": country, "applicable": False,
                "demand_multiplier": 1.0,
                "message": "Only BR supported in MVP"}

    h = _holiday_signal(today)
    s = _seasonality_signal(category)

    # α_s > α_h: long-run seasonality (24 months of category data) is more
    # statistically reliable than holiday proximity (single calendar event).
    # Sensitivity is reported below across α_h ∈ {0.2, 0.4, 0.6} so reviewers
    # can see how much these specific weights matter.
    ALPHA_H = 0.4
    ALPHA_S = 0.6
    demand_mult = ALPHA_H * h["holiday_multiplier"] + ALPHA_S * s["seasonality_multiplier"]
    demand_mult = max(0.5, min(1.8, demand_mult))   # clamp to plausible range

    # Sensitivity bracket: α_h ∈ {0.2, 0.4, 0.6} centered on the 0.4 default.
    # Spans seasonality-dominant (α_h=0.2) ↔ holiday-dominant (α_h=0.6) ↔
    # balanced (α_h=0.4). Reviewer can see how the chosen weight matters in
    # absolute terms — typical spread is small (<0.05) when both signals agree.
    sensitivity = {}
    for alpha_h in [0.2, 0.4, 0.6]:
        alpha_s = 1.0 - alpha_h
        m = alpha_h * h["holiday_multiplier"] + alpha_s * s["seasonality_multiplier"]
        label = f"alpha_h={alpha_h}" + (" (default)" if alpha_h == ALPHA_H else "")
        sensitivity[label] = round(max(0.5, min(1.8, m)), 3)

    return {
        "category": category,
        "country": country,
        "applicable": True,
        "demand_multiplier": round(demand_mult, 3),
        "formula": f"demand = {ALPHA_H}*holiday_mult + {ALPHA_S}*seasonality_mult",
        "weights": {"alpha_holiday": ALPHA_H, "alpha_seasonal": ALPHA_S},
        "holiday": h,
        "seasonality": s,
        "sensitivity_analysis": sensitivity,
        "rationale": (f"holiday={h['holiday_multiplier']} & "
                      f"seasonal={s['seasonality_multiplier']} "
                      f"-> demand={round(demand_mult, 3)}"),
    }
