"""PriceIQ Tool 2 — calculate_price_elasticity (v2, log-log OLS).

Model:
  Naive:      ln(Q_t) = α + β·ln(P_t) + ε_t
  Controlled: ln(Q_t) = α + β·ln(P_t) + γ·freight_t + ε_t

Multicollinearity diagnostic (response to instructor comment #1):
  unstable := sign-flip(β_naive, β_ctrl)  OR  |Δβ| > 1.0
  if unstable: fall back to naive β + raise multicollinearity_warning

PVC v1 → v2: v1 used 7 predictors (ln_p + freight + installments + 3 quarter
dummies + const) on n=21 months → low df + collinearity → β flipped sign.
v2 collapses to 1 control (`avg_freight`) and adds the diagnostic.

Public API:
    calculate_price_elasticity(category, monthly_panel=None,
                               start_date=None, end_date=None) -> dict
        Includes: elasticity_beta, ci_95, p_value, multicollinearity_warning,
        recommended_source, naive_beta, controlled_beta, causal_caveat (verbatim).
"""

import os
from typing import Optional


def calculate_price_elasticity(
    category: str,
    monthly_panel: Optional[list] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> dict:
    """估计价格弹性 β，附 multicollinearity 诊断 + 推荐 β。"""
    if monthly_panel is None:
        from priceiq_data import query_sales_data
        d = query_sales_data(category, start_date, end_date)
        if not d.get("found"):
            return {"category": category, "success": False,
                    "message": d.get("message", "No data")}
        monthly_panel = d["monthly_panel"]

    # Need ≥8 monthly observations: controlled OLS uses 3 parameters (const +
    # ln_p + freight), leaving ≥5 residual degrees of freedom for stable CIs.
    # Below that, t-stats become meaningless even when the point estimate fits.
    if len(monthly_panel) < 8:
        return {"category": category, "success": False,
                "message": f"Insufficient panel: {len(monthly_panel)} months (need >= 8)"}

    import numpy as np
    import pandas as pd
    import statsmodels.api as sm

    df = pd.DataFrame(monthly_panel)
    df = df[(df["avg_price"] > 0) & (df["n_orders"] > 0)].copy()
    df["ln_q"] = np.log(df["n_orders"])
    df["ln_p"] = np.log(df["avg_price"])

    # ── 模型 A: naive log-log ─────────────────────────────
    X_simple = sm.add_constant(df[["ln_p"]].astype(float))
    m_simple = sm.OLS(df["ln_q"].values, X_simple).fit()

    # ── 模型 B: 单控制 (freight) ──────────────────────────
    # NOTE: v1 also included `avg_installments` and 3 quarter dummies → 7
    # predictors with n=21 hit multicollinearity (F-02). v2 reduced to a single
    # control (`avg_freight`) — captures the most-correlated confounder while
    # leaving plenty of residual df. See PVC_Log.md for the full v1→v2 trace.
    X_full = sm.add_constant(df[["ln_p", "avg_freight"]].astype(float))
    m_full = sm.OLS(df["ln_q"].values, X_full).fit()

    beta_naive = float(m_simple.params["ln_p"])
    beta_ctrl = float(m_full.params["ln_p"])

    # ── Multicollinearity / instability diagnostic ───────────
    # When `freight_value` is highly correlated with `ln_p` (often true in Olist —
    # higher-priced categories tend to have higher freight), the controlled OLS
    # can't cleanly separate effects. Symptoms: β flips sign, or |Δβ| explodes.
    # In those cases we honestly report the simpler naive estimate + a warning,
    # rather than a "controlled-but-wrong" number.
    sign_flipped = (beta_naive < 0) != (beta_ctrl < 0)
    big_jump = abs(beta_ctrl - beta_naive) > 1.0
    unstable = sign_flipped or big_jump

    if unstable:
        # Fallback to naive: less precision, but no spurious controlled effect.
        m = m_simple
        recommended_beta = beta_naive
        source = "naive (controlled model unstable: sign-flip or |Δβ|>1.0)"
    else:
        m = m_full
        recommended_beta = beta_ctrl
        source = "controlled with avg_freight"

    se = float(m.bse["ln_p"])
    ci_lo, ci_hi = m.conf_int(alpha=0.05).loc["ln_p"]
    p_val = float(m.pvalues["ln_p"])

    abs_beta = abs(recommended_beta)
    label = ("highly elastic" if abs_beta > 1.5 else
            "elastic" if abs_beta > 1.0 else
            "inelastic" if abs_beta > 0.5 else
            "very inelastic")

    return {
        "category": category,
        "success": True,
        "n_observations": int(len(df)),
        "elasticity_beta": round(recommended_beta, 3),
        "recommended_source": source,
        "naive_beta": round(beta_naive, 3),
        "controlled_beta": round(beta_ctrl, 3),
        "controls_changed_beta_by": round(beta_ctrl - beta_naive, 3),
        "multicollinearity_warning": unstable,
        "std_error": round(se, 3),
        "ci_95": [round(float(ci_lo), 3), round(float(ci_hi), 3)],
        "p_value": round(p_val, 4),
        "significance": "significant (p<0.05)" if p_val < 0.05 else "not significant",
        "r_squared": round(float(m.rsquared), 3),
        "elasticity_label": label,
        "control_variables": ["avg_freight"] if not unstable else [],
        "causal_caveat": (
            "ASSOCIATIONAL ONLY -- not causal. Historical price variation in Olist "
            "data is confounded by promotions, freight policy changes, seasonality, "
            "and supply shocks we cannot fully observe. This beta reflects "
            "price-quantity correlation under the chosen control set, but does NOT "
            "prove that lowering price by 10%% will causally lift quantity by |beta|*10%%. "
            "Use as a directional indicator for pricing decisions, not as a causal estimate. "
            "A controlled A/B pricing experiment would be required for causal inference."
        ),
    }
