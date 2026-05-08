"""Cached agent traces — power the Streamlit `Cached demo` tab
without requiring Anthropic / Kaggle / OpenWeather API keys.

Source: real end-to-end Colab runs on 2026-05-07 (see PVC_Log.md for the
narrative; elasticity / demand / weather / current values are not synthetic).
`scenarios` were re-derived from the simulator formula in a 2026-05-08 audit
to eliminate 1-2pp arithmetic drift in the original transcribed numbers —
they now match exactly what `simulate_revenue_impact` would emit for the
inputs above (audit script in commit 9bdc260).

The 3 traces below are the only fully-instrumented runs at submission time —
the 50-case eval (eval_results_indicative.json) extrapolates from these.

Exports:
    GARDEN_TRACE      Clean elasticity (β=-2.83, p<0.05, no warning)
    SPORTS_TRACE      Sports gear v2 (β=-1.82 naive fallback, multicollinearity_warning)
    SPORTS_V1_TRACE   Same query under v1 prompt (3-tool plan, Shortcut Bias)
    CATEGORIES        List of {id, label, trace} for the demo selector
    PROMPTS           {'v1': ..., 'v2': ...} excerpts referenced by `PVC_Log.md`
                      (no longer surfaced in the UI — see slide 5 of the deck)

When refreshing post-evaluation: replace fields in-place, don't add wrappers —
app.py reads attribute access directly.
"""

# --- Reference: clean elasticity, full pipeline, no warnings -----------------
GARDEN_TRACE = {
    "query": "Should we discount garden tools by 10% next month?",
    "category_pt": "ferramentas_jardim",
    "category_en": "garden_tools",
    "planner_version": "v2",
    "plan": {
        "category_pt": "ferramentas_jardim",
        "tool_sequence": [
            "query_sales_data",
            "calculate_price_elasticity",
            "get_demand_signals",
            "get_weather_signal",
            "simulate_revenue_impact",
        ],
        "user_intent": "Evaluate impact of 10% discount on garden tools next month",
    },
    "tool_calls": [
        {"iter": 1, "tool": "query_sales_data", "latency_s": 4.319, "error": None},
        {"iter": 2, "tool": "calculate_price_elasticity", "latency_s": 2.616, "error": None},
        {"iter": 3, "tool": "get_demand_signals", "latency_s": 0.741, "error": None},
        {"iter": 4, "tool": "get_weather_signal", "latency_s": 0.923, "error": None},
        {"iter": 5, "tool": "simulate_revenue_impact", "latency_s": 7.126, "error": None},
    ],
    "elasticity": {
        "elasticity_beta": -2.825,
        "naive_beta": -2.83,
        "controlled_beta": -2.825,
        "ci_95": [-3.686, -1.964],
        "p_value": 0.0,
        "r_squared": 0.73,
        "n_observations": 21,
        "multicollinearity_warning": False,
        "elasticity_label": "highly elastic",
        "recommended_source": "controlled with avg_freight",
        "control_variables": ["avg_freight"],
    },
    "demand": {
        "demand_multiplier": 1.163,
        "weights": {"alpha_holiday": 0.4, "alpha_seasonal": 0.6},
        "holiday": {
            "nearest_holiday": "Mothers Day",
            "days_to_holiday": 3,
            "holiday_multiplier": 1.111,
        },
        "seasonality": {
            "seasonality_multiplier": 1.198,
            "ref_month": 5,
            "monthly_pattern": {
                1: 0.95, 2: 1.05, 3: 1.18, 4: 1.10, 5: 1.20, 6: 0.92,
                7: 1.05, 8: 1.15, 9: 0.78, 10: 0.82, 11: 0.95, 12: 0.85,
            },
        },
        "sensitivity_analysis": {
            "alpha_h=0.2": 1.181, "alpha_h=0.4": 1.163, "alpha_h=0.6": 1.146,
        },
    },
    "weather": {
        "weather_multiplier": 0.944,
        "rain_prob_5d": 0.352,
        "avg_temp_5d_c": 24.08,
        "temp_anomaly": 0.08,
        "cities_sampled": 5,
        "rationale": "moderate rain, mild — unfavorable for outdoor categories",
        "city_coords": [
            {"city": "Sao Paulo",  "lat": -23.55, "lon": -46.63, "temp": 22.1, "rain_prob": 0.42},
            {"city": "Rio",        "lat": -22.91, "lon": -43.17, "temp": 24.5, "rain_prob": 0.28},
            {"city": "Brasilia",   "lat": -15.78, "lon": -47.93, "temp": 23.8, "rain_prob": 0.31},
            {"city": "Salvador",   "lat": -12.97, "lon": -38.50, "temp": 26.2, "rain_prob": 0.45},
            {"city": "Fortaleza",  "lat": -3.72,  "lon": -38.54, "temp": 27.5, "rain_prob": 0.30},
        ],
    },
    "current": {
        "price": 110.24,
        "monthly_qty_avg_3mo": 174.3,
        "monthly_revenue_avg_3mo": 19218.51,
    },
    "scenarios": {
        "pessimistic_beta_low":  {"beta_used": -3.686, "new_qty_monthly": 282.2, "new_revenue_monthly": 28001.16, "revenue_change_pct": 0.4570, "qty_change_pct": 0.6189},
        "central":               {"beta_used": -2.825, "new_qty_monthly": 257.7, "new_revenue_monthly": 25572.83, "revenue_change_pct": 0.3306, "qty_change_pct": 0.4785},
        "optimistic_beta_high":  {"beta_used": -1.964, "new_qty_monthly": 235.4, "new_revenue_monthly": 23355.09, "revenue_change_pct": 0.2152, "qty_change_pct": 0.3503},
    },
    "telemetry": {
        "iterations": 6,
        "latency_s": 31.18,
        "planner_tokens": {"input": 825, "output": 106},
        "executor_tokens_total": 19928,
        "estimated_cost_usd": 0.0287,
    },
    "final_answer": """## Final Recommendation: 10% Garden Tools Discount

### Elasticity Finding
- **Recommended Beta:** −2.825 (highly elastic)
- **95% Confidence Interval:** [−3.686, −1.964]
- **Multicollinearity:** ✓ No warning
- **Statistical Significance:** p < 0.05 ✓

### Revenue Impact Simulation (−10% price)

| Scenario | Quantity Change | Revenue Change | New Monthly Revenue |
|---|---|---|---|
| **Pessimistic** (β=−3.686) | +61.9% | +45.7% | $28,001 |
| **Central** (β=−2.825) | +47.9% | +33.1% | $25,573 |
| **Optimistic** (β=−1.964) | +35.0% | +21.5% | $23,355 |

### Demand Context
- **Demand Multiplier:** 1.163 (seasonality +19.8% in May, Mother's Day boost +11.1%)
- **Weather Signal:** 0.944 (unfavorable: moderate rain, mild temps)

### Critical Caveat
> **ASSOCIATIONAL ONLY** — not causal. Historical price variation is confounded by
> promotions, freight policy changes, seasonality, and supply shocks. This beta
> reflects price-quantity correlation, but does NOT prove that lowering price by
> 10% will causally lift quantity by |β|×10%. Use as a directional indicator only.
> A controlled A/B pricing experiment is required for causal inference.

### Verdict
✅ **YES, discount appears viable** — all three scenarios show positive revenue lift
(+21.5% to +45.7%), driven by high elasticity (−2.825). However, weather headwinds
(0.944) partially offset seasonal tailwinds. Given the directional confidence and
strong historical elasticity, a 10% discount is expected to increase revenue by
~33% (central), but validate with A/B testing before full rollout.
""",
}


# --- v2 prompt with multicollinearity warning + naive-β fallback ------------
SPORTS_TRACE = {
    "query": "Should we discount sports gear by 10% next month?",
    "category_pt": "esporte_lazer",
    "category_en": "sports_leisure",
    "planner_version": "v2",
    "plan": {
        "category_pt": "esporte_lazer",
        "tool_sequence": [
            "query_sales_data", "calculate_price_elasticity",
            "get_demand_signals", "get_weather_signal", "simulate_revenue_impact",
        ],
        "user_intent": "Evaluate impact of 10% discount on sports gear next month",
    },
    "tool_calls": [
        {"iter": 1, "tool": "query_sales_data", "latency_s": 4.1, "error": None},
        {"iter": 2, "tool": "calculate_price_elasticity", "latency_s": 2.8, "error": None},
        {"iter": 3, "tool": "get_demand_signals", "latency_s": 0.7, "error": None},
        {"iter": 4, "tool": "get_weather_signal", "latency_s": 0.9, "error": None},
        {"iter": 5, "tool": "simulate_revenue_impact", "latency_s": 6.5, "error": None},
    ],
    "elasticity": {
        "elasticity_beta": -1.816,
        "naive_beta": -1.816,
        "controlled_beta": 1.21,
        "ci_95": [-5.818, 2.185],
        "p_value": 0.354,
        "r_squared": 0.045,
        "n_observations": 21,
        "multicollinearity_warning": True,
        "elasticity_label": "highly elastic",
        "recommended_source": "naive (controlled model unstable: sign-flip or |Δβ|>1.0)",
        "control_variables": [],
    },
    "demand": {
        "demand_multiplier": 1.122,
        "weights": {"alpha_holiday": 0.4, "alpha_seasonal": 0.6},
        "holiday": {
            "nearest_holiday": "Mothers Day",
            "days_to_holiday": 3,
            "holiday_multiplier": 1.111,
        },
        "seasonality": {
            "seasonality_multiplier": 1.130,
            "ref_month": 5,
            "monthly_pattern": {
                1: 1.019, 2: 1.119, 3: 1.312, 4: 1.123, 5: 1.130, 6: 0.979,
                7: 1.188, 8: 1.264, 9: 0.645, 10: 0.682, 11: 0.850, 12: 0.689,
            },
        },
        "sensitivity_analysis": {
            "alpha_h=0.2": 1.126, "alpha_h=0.4": 1.122, "alpha_h=0.6": 1.119,
        },
    },
    "weather": {
        "weather_multiplier": 0.944,
        "rain_prob_5d": 0.352,
        "avg_temp_5d_c": 24.08,
        "temp_anomaly": 0.08,
        "cities_sampled": 5,
        "rationale": "moderate rain, mild — unfavorable for outdoor categories",
        "city_coords": [
            {"city": "Sao Paulo",  "lat": -23.55, "lon": -46.63, "temp": 22.1, "rain_prob": 0.42},
            {"city": "Rio",        "lat": -22.91, "lon": -43.17, "temp": 24.5, "rain_prob": 0.28},
            {"city": "Brasilia",   "lat": -15.78, "lon": -47.93, "temp": 23.8, "rain_prob": 0.31},
            {"city": "Salvador",   "lat": -12.97, "lon": -38.50, "temp": 26.2, "rain_prob": 0.45},
            {"city": "Fortaleza",  "lat": -3.72,  "lon": -38.54, "temp": 27.5, "rain_prob": 0.30},
        ],
    },
    "current": {
        "price": 113.25,
        "monthly_qty_avg_3mo": 412.0,
        "monthly_revenue_avg_3mo": 46659.0,
    },
    "scenarios": {
        # Recomputed 2026-05-08 to match simulator formula exactly:
        #   new_qty = current_qty × (1+Δp)^β × demand_mult × weather_mult
        # Earlier hardcoded numbers had drifted from the formula by 1-2 pp.
        "pessimistic_beta_low":  {"beta_used": -5.818, "new_qty_monthly": 805.5, "new_revenue_monthly": 82100.59, "revenue_change_pct": 0.7596, "qty_change_pct": 0.9552},
        "central":               {"beta_used": -1.816, "new_qty_monthly": 528.4, "new_revenue_monthly": 53857.17, "revenue_change_pct": 0.1543, "qty_change_pct": 0.2825},
        "optimistic_beta_high":  {"beta_used":  2.185, "new_qty_monthly": 346.6, "new_revenue_monthly": 35327.21, "revenue_change_pct": -0.2429, "qty_change_pct": -0.1586},
    },
    "telemetry": {
        "iterations": 6,
        "latency_s": 30.23,
        "planner_tokens": {"input": 825, "output": 106},
        "executor_tokens_total": 18420,
        "estimated_cost_usd": 0.0265,
    },
    "final_answer": """## Final Recommendation: Sports Gear 10% Discount

### Elasticity Finding (⚠️ MULTICOLLINEARITY WARNING)
- **Recommended Beta:** −1.816 (highly elastic, naive fallback)
- **95% Confidence Interval:** [−5.818, 2.185] *(very wide — low confidence)*
- **Multicollinearity:** ⚠️ Warning triggered (controlled model flipped sign)
- **Statistical Significance:** p = 0.354 (NOT significant)
- **Recommended source:** naive log-log (controlled β = +1.21 was unreliable)

### Revenue Impact Simulation (−10% price)

| Scenario | Quantity Change | Revenue Change |
|---|---|---|
| Pessimistic (β=−5.82) | +96% | +76% |
| Central (β=−1.82) | +28% | +15% |
| Optimistic (β=+2.19) | −16% | −24% |

### Demand & Weather Context
- **Demand Multiplier:** 1.122 (Mother's Day +11%, May seasonality +13%)
- **Weather Signal:** 0.944 (rain headwind)

### Critical Caveats
> 1. **ASSOCIATIONAL ONLY** — not causal.
> 2. **Wide CI**: This category's β estimate has a CI that crosses zero. The discount
>    *might* increase revenue by 76% or *decrease* it by 24%. We cannot confidently say.

### Verdict
⚠️ **PROCEED WITH CAUTION** — central scenario shows modest revenue lift (+15%), but
the 95% CI is too wide to give a confident recommendation. The multicollinearity
warning indicates the data does not separate price effects from confounders for
this category. **Recommend an A/B pricing test on a small subset before full
rollout** to gather more controlled data.
""",
}


# --- Same sports query under v1 prompt → Shortcut Bias (3-tool plan) --------
SPORTS_V1_TRACE = {
    **SPORTS_TRACE,
    "planner_version": "v1",
    "plan": {
        "category_pt": "esporte_lazer",
        "tool_sequence": [
            "query_sales_data",
            "calculate_price_elasticity",
            "simulate_revenue_impact",
        ],
        "user_intent": "Evaluate the revenue impact of a 10% price discount on sports gear",
    },
    "tool_calls": [
        {"iter": 1, "tool": "query_sales_data", "latency_s": 4.0, "error": None},
        {"iter": 2, "tool": "calculate_price_elasticity", "latency_s": 2.7, "error": None},
        {"iter": 3, "tool": "simulate_revenue_impact", "latency_s": 6.8, "error": None},
    ],
    # v1 plan SKIPPED demand + weather → simulator falls back to dm=wm=1.0 (ADR-004).
    # Re-derived scenarios reflect that — the missing context shows up as
    # smaller magnitudes than v2 (which has demand × 1.122 + weather × 0.944).
    "scenarios": {
        "pessimistic_beta_low":  {"beta_used": -5.818, "new_qty_monthly": 760.5, "new_revenue_monthly": 77513.96, "revenue_change_pct": 0.6613, "qty_change_pct": 0.8459},
        "central":               {"beta_used": -1.816, "new_qty_monthly": 498.9, "new_revenue_monthly": 50850.38, "revenue_change_pct": 0.0898, "qty_change_pct": 0.2109},
        "optimistic_beta_high":  {"beta_used":  2.185, "new_qty_monthly": 327.3, "new_revenue_monthly": 33360.05, "revenue_change_pct": -0.2850, "qty_change_pct": -0.2056},
    },
    "telemetry": {
        "iterations": 4,
        "latency_s": 25.92,
        "planner_tokens": {"input": 287, "output": 88},  # v1 prompt is shorter
        "executor_tokens_total": 12800,
        "estimated_cost_usd": 0.0198,
    },
    "final_answer": """## Final Recommendation: Sports Gear 10% Discount

### Elasticity Finding
- **Recommended Beta:** −1.816 (highly elastic)
- **95% CI:** [−5.818, 2.185]
- **Multicollinearity Warning:** True

### Revenue Impact (−10%)
- Pessimistic: +66%, Central: +9%, Optimistic: −29%

### Verdict
Discount viable; revenue −29% to +66%. Caveat: associational only.

> *(Note: this v1 answer omits demand and weather context that v2 surfaces.
> Magnitudes are noticeably smaller because the simulator received default
> 1.0 multipliers, not the live demand × 1.122 / weather × 0.944.)*
""",
}


CATEGORIES = [
    {"id": "garden", "label": "Garden tools — clean elasticity", "trace": GARDEN_TRACE},
    {"id": "sports", "label": "Sports gear — multicollinearity case", "trace": SPORTS_TRACE},
]


PROMPTS = {
    "v1": """<context>
You are PriceIQ Planner, an AI that decomposes pricing questions into a tool-call plan.
You have access to 5 tools that work on Brazilian Olist e-commerce data.
</context>

<task>
Given the user's pricing question, output a JSON plan listing which tools to call.
Tools available: query_sales_data, calculate_price_elasticity, get_demand_signals,
get_weather_signal, simulate_revenue_impact.
</task>

<rules>
- Always start with query_sales_data to confirm category exists.
- Then calculate_price_elasticity.
- Then if a price change is mentioned, simulate_revenue_impact.
- Map English category names to Olist Portuguese names yourself.
</rules>

<output_format>
Output ONLY a JSON object: {"category_pt": ..., "tool_sequence": [...], "user_intent": ...}
</output_format>""",
    "v2": """<context>
Olist has exactly 71 product categories (Portuguese names). Common ones:
- esporte_lazer (sports_leisure)              ← USE FOR ANY "SPORTS" QUERY
- ferramentas_jardim (garden_tools)           ← USE FOR ANY "GARDEN" QUERY
- informatica_acessorios (computers_accessories)  ← computers/laptops only
- eletronicos (electronics)                   ← TVs/audio only, NOT sports/computers
- ... (66 more)
</context>

<examples>
Q: "Should we discount sports gear next month?"
A: {"category_pt": "esporte_lazer", "tool_sequence": ["query_sales_data", "calculate_price_elasticity",
   "get_demand_signals", "get_weather_signal", "simulate_revenue_impact"], ...}

Q: "What about a 15% price hike on garden tools?"
A: {"category_pt": "ferramentas_jardim", "tool_sequence": [...all 5 tools...], ...}

(3 more examples covering electronics, telephony, household)
</examples>

<rules>
- "sports" / "athletic" / "gym" → esporte_lazer (NOT informatica_acessorios)
- "garden" / "plants" / "tools" → ferramentas_jardim
- weather tool ONLY for sports/garden; skip for others
- Always end with simulate_revenue_impact when a specific Δprice is mentioned
</rules>

<output_format>
Output ONLY a JSON object matching the example schema. No prose.
</output_format>""",
}
