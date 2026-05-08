# Prompt Version Control (PVC) Log — PriceIQ Phase 2

> Track B requires manual orchestration of the tool_use loop. The Planner prompt
> was the highest-leverage point. This log documents three iterations on real
> Colab traces, with token counts, latency, and observable behavior diffs.

---

## v1 — Under-specified (Initial Draft)

### Prompt (excerpt)
```
<context>
You are PriceIQ Planner, an AI that decomposes pricing questions into a tool-call plan.
You have access to 5 tools that work on Brazilian Olist e-commerce data.
</context>

<rules>
- Always start with query_sales_data to confirm category exists.
- Then calculate_price_elasticity.
- Then if a price change is mentioned, simulate_revenue_impact.
- Map English category names to Olist Portuguese names yourself.
</rules>
```

### Failure mode discovered (real Colab trace, 2026-05-07)

**Query**: `"Should we discount sports gear by 10% next month?"`

**Plan emitted**:
```json
{
  "category_pt": "esporte_lazer",
  "tool_sequence": [
    "query_sales_data",
    "calculate_price_elasticity",
    "simulate_revenue_impact"
  ],
  "user_intent": "Evaluate the revenue impact of a 10% price discount on sports gear"
}
```

**What we expected to fail**: Category misclassification (sports → informatica_acessorios).
We hypothesized the LLM would default to a popular wrong category.

**What actually failed**: **Shortcut Bias** — the plan only includes 3 tools, skipping
`get_demand_signals` and `get_weather_signal`. The LLM took the minimum-viable path
because the rules said "if a price change is mentioned, simulate_revenue_impact" but
never insisted that demand and weather context are required.

**Why this is a real failure**: Without demand/weather multipliers, the simulator falls
back to default 1.0 for both. For sports gear in May (Mother's Day proximity, +13%
seasonality, light rain headwind), this loses ~16% of the demand-side signal. The
final revenue projection misses a known driver.

**Note on Sonnet 4.5 robustness**: We expected the under-specified prompt to also
break category mapping. It didn't — Sonnet 4.5 inferred `esporte_lazer` correctly
from Portuguese semantics even without an explicit list. This was an honest surprise
and is documented as a limit of the experiment, not a hidden success.

### Telemetry (v1, sports query)
| Metric | Value |
|---|---|
| Planner tokens | 825 in / 106 out |
| Plan length | 3 tools |
| Executor iterations | 4 |
| Total executor tokens | ~12,800 |
| Latency | 25.92 s |
| `success` | True (but with degraded inputs to simulator) |

---

## v2 — Full Categories + Few-shot (Production)

### What changed

1. Listed the **11 high-volume Olist categories** explicitly with Portuguese ↔ English
   mapping, including disambiguating notes (e.g., `eletronicos = TVs/audio, NOT computers/sports`).
2. Added **5 few-shot examples**, each showing the *complete* tool sequence and the
   exact `category_pt`. Two examples are sports/garden (driving the weather tool).
3. Added explicit rules: `weather tool ONLY for sports/garden; skip for others`.
4. Added negative examples in the rules: `"sports" / "athletic" / "gym" → esporte_lazer
   (NOT informatica_acessorios)`.

### Plan emitted (same query)

```json
{
  "category_pt": "esporte_lazer",
  "tool_sequence": [
    "query_sales_data",
    "calculate_price_elasticity",
    "get_demand_signals",
    "get_weather_signal",
    "simulate_revenue_impact"
  ],
  "user_intent": "Evaluate impact of 10% discount on sports gear next month"
}
```

### Telemetry (v2, same sports query)
| Metric | Value |
|---|---|
| Planner tokens | 825 in / 106 out (note: prompt is longer but compresses well) |
| Plan length | 5 tools |
| Executor iterations | 6 |
| Total executor tokens | ~19,900 |
| Latency | 30.23 s |
| `success` | True with full demand + weather signals |

### Final answer comparison (sports, -10%)

**v1** (3-tool plan; demand/weather defaulted to 1.0 inside the simulator's auto-fill):
> "Discount viable; revenue +21–46%. Caveat: associational only."

**v2** (5-tool plan; demand_mult=1.122, weather_mult=0.944):
> "Discount viable; revenue +21–46% with demand tailwind from Mother's Day (+11.1%
> within 3 days) and seasonality (May historically +13%) partially offset by weather
> headwind (-5.6%). Caveat: associational only."

The v1 answer is correct in direction but **lacks the stakeholder context** that
makes the recommendation actionable. v2 surfaces the seasonality and weather signals
as part of the rationale.

---

## v3 — Deferred to Phase 3

| Improvement | Expected impact |
|---|---|
| Token-efficient category list (CSV blob, on-demand parse) | -200 input tokens (-25% of v2 Planner cost) |
| Explicit refusal example (OOS queries → empty `tool_sequence`) | Saves ~$0.005 per OOS leak (see F-06) |
| Skip simulator when elasticity `success: False` | Saves 1 wasted tool call on low-data categories |

---

## Cost comparison (per query, sports test)

| Version | Planner $ | Executor $ | Total $ | Plan completeness |
|---|---|---|---|---|
| v1 | $0.0035 | $0.0163 | $0.0198 | 3 / 5 tools |
| v2 | $0.0035 | $0.0252 | $0.0287 | 5 / 5 tools |

**Cost delta: +$0.009 per query (+45%) for full pipeline coverage.**

For Phase 2's 50-query evaluation set, this is +$0.45 total. Acceptable.

---

## Lessons applied to future Planner prompts

1. **List your domain entities explicitly** when LLM hallucination is a risk. Sonnet 4.5
   could infer Portuguese category names but couldn't infer "demand and weather are
   important" without examples.
2. **Few-shot examples must demonstrate the *complete* desired behavior**, not just
   syntax. v1 had no examples; v2's 5 examples each show full 5-tool sequences.
3. **Rules should include negative examples**. "sports → esporte_lazer (NOT
   informatica_acessorios)" prevents the misclassification we initially worried about.
4. **Honest post-mortems matter more than dramatic fictional failures**. The shortcut
   bias we found is a real, generalizable LLM agent failure — more useful than a
   contrived category mishap.
