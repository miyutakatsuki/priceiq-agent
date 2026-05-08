"""PriceIQ Tool 5 — simulate_revenue_impact (3-scenario CI propagation).

Combines elasticity β + demand_multiplier + weather_multiplier into a
forward simulation of a proposed price change.

Formula:
    new_qty     = current_qty × (1+Δp)^β × demand_mult × weather_mult
    new_revenue = new_qty × current_price × (1+Δp)
    Δrevenue%   = new_revenue / current_revenue − 1

Three scenarios from β's 95% CI:
    pessimistic_beta_low · central · optimistic_beta_high

Public API:
    simulate_revenue_impact(category, price_change_pct,
                            elasticity=None, demand_signal=None,
                            weather_signal=None) -> dict
        If upstream signals are omitted, the simulator self-fetches them.
        Returns scenarios + formula + caveat (complementary to elasticity's caveat).
"""

from typing import Optional


def simulate_revenue_impact(
    category: str,
    price_change_pct: float,
    elasticity: Optional[dict] = None,
    demand_signal: Optional[dict] = None,
    weather_signal: Optional[dict] = None,
) -> dict:
    """模拟价格变动 Δp 对收益的影响（含 3 场景）。

    Args:
        category: 葡语品类名
        price_change_pct: 价格变动比例（-0.10 = 降价 10%）。
            合理范围 [-0.5, +0.5]；超过会触发数学奇点（dp=-1 时 (1+dp)^β=0^β
            div-by-zero for β<0）或不可信外推（dp=-0.9 + β=-3 → factor=1000）。
            超界时返回 success=False。
        elasticity / demand_signal / weather_signal: 上游工具输出，
            未提供时自动调用对应 Tool。

    Returns:
        含 current / new_price / scenarios（3 个）+ formula + caveat 的 dict。
    """
    # Validate input range — refuse extreme deltas to avoid math singularities
    if not (-0.5 <= price_change_pct <= 0.5):
        return {"category": category, "success": False,
                "message": (f"price_change_pct={price_change_pct} outside [-0.5, +0.5]. "
                            "Extreme price changes produce non-credible projections; "
                            "consider running multiple smaller deltas instead.")}

    if elasticity is None:
        from priceiq_elasticity import calculate_price_elasticity
        elasticity = calculate_price_elasticity(category)
    if not elasticity.get("success"):
        return {"category": category, "success": False,
                "message": f"Elasticity unavailable: {elasticity.get('message','?')}"}

    if demand_signal is None:
        from priceiq_demand import get_demand_signals
        demand_signal = get_demand_signals(category)
    if weather_signal is None:
        from priceiq_weather import get_weather_signal
        weather_signal = get_weather_signal(category)

    # Pull baseline state (price + 3-month-avg quantity) from Tool 1
    from priceiq_data import query_sales_data
    sales = query_sales_data(category)
    if not sales.get("found"):
        return {"category": category, "success": False, "message": "No sales data"}

    current_price = sales["price_stats"]["mean"]
    monthly = [m["n_orders"] for m in sales["monthly_panel"][-3:]]   # last 3 months
    current_qty = sum(monthly) / len(monthly)
    current_revenue = current_qty * current_price

    # CI bounds drive the pessimistic / optimistic scenarios; β_central is the
    # recommended point estimate (already accounts for multicollinearity fallback).
    beta_central = elasticity["elasticity_beta"]
    ci = elasticity.get("ci_95", [beta_central, beta_central])
    beta_lo, beta_hi = ci

    # Default 1.0 = neutral (no signal). This is the documented degraded
    # behavior (ADR-004): if Tool 3 / Tool 4 returned partial output, the
    # simulator still produces a directional answer rather than aborting.
    demand_mult = demand_signal.get("demand_multiplier", 1.0)
    weather_mult = weather_signal.get("weather_multiplier", 1.0)

    delta_p = price_change_pct
    new_price = current_price * (1 + delta_p)

    def _scenario(beta):
        """Compute one revenue scenario for a given β; closes over current_*, mults, delta_p."""
        qty_factor = (1 + delta_p) ** beta * demand_mult * weather_mult
        new_qty = current_qty * qty_factor
        new_revenue = new_qty * new_price
        # Rounding convention: β to 3dp (statistical precision), qty to 1dp
        # (whole-unit-ish), revenue to 2dp ($cents), pct change to 4dp (4 sig fig).
        return {
            "beta_used": round(beta, 3),
            "new_qty_monthly": round(new_qty, 1),
            "new_revenue_monthly": round(new_revenue, 2),
            "revenue_change_pct": round(new_revenue / current_revenue - 1, 4),
            "qty_change_pct": round(qty_factor - 1, 4),
        }

    return {
        "category": category,
        "success": True,
        "price_change_pct": price_change_pct,
        "current": {
            "price": round(current_price, 2),
            "monthly_qty_avg_3mo": round(current_qty, 1),
            "monthly_revenue_avg_3mo": round(current_revenue, 2),
        },
        "new_price": round(new_price, 2),
        "elasticity_beta_central": beta_central,
        "elasticity_ci_95": ci,
        "demand_multiplier": demand_mult,
        "weather_multiplier": weather_mult,
        # Keys are named after which β CI end is used (statistics POV). The
        # *revenue* ordering of these three is NOT guaranteed — for an elastic
        # good with a price decrease, β_low (most elastic) gives the *highest*
        # revenue. The Streamlit UI re-sorts by revenue and labels with
        # user-facing Pessimistic / Central / Optimistic. Don't rely on the
        # dict-key order to mean "low → high revenue".
        "scenarios": {
            "pessimistic_beta_low":  _scenario(beta_lo),
            "central":               _scenario(beta_central),
            "optimistic_beta_high":  _scenario(beta_hi),
        },
        "formula": "new_qty = current_qty * (1+dp)^beta * demand_mult * weather_mult",
        "caveat": (
            "Forward simulation based on log-log elasticity. Results are "
            "DIRECTIONAL not CAUSAL predictions. CI bounds reflect statistical "
            "uncertainty in beta only; demand/weather multiplier uncertainty is "
            "not propagated. Use alongside elasticity tool's causal_caveat."
        ),
    }
