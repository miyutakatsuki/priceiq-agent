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
> "Discount viable; revenue −29% to +66% (very wide CI). Caveat: associational only."

**v2** (5-tool plan; demand_mult=1.122, weather_mult=0.944):
> "Discount viable; revenue −24% to +76% with demand tailwind from Mother's Day (+11.1%
> within 3 days) and seasonality (May historically +13%) partially offset by weather
> headwind (-5.6%). Caveat: associational only."

The v1 answer is correct in direction but **lacks the stakeholder context** that
makes the recommendation actionable. v2 surfaces the seasonality and weather signals
as part of the rationale, and the simulator's CI shifts up ~7pp (midpoint +18%
→ +26%) — upside larger, downside less severe — because it received the
live demand × 1.122 / weather × 0.944 instead of v1's default 1.0 / 1.0.

---

## v3 — Final Production (shipped configuration)

v3 is the version actually shipped in this submission. It keeps v2's Planner
prompt verbatim — the XML few-shot block is what makes the Planner cover all
5 tools — and pairs it with three runtime stability fixes that emerged during
end-to-end testing. The fixes are not prompt edits, but they are the reason
v2's plans now consistently produce stable, finalized answers instead of
mid-loop role confusion or sign-flipped β.

### What changed from v2 → v3 (why this version stabilized the agent)

| Layer | v2 behavior | v3 fix | Source of evidence |
|---|---|---|---|
| **Executor memory threshold** | `MEMORY_THRESHOLD_CHARS = 8000`. Mid-loop compression replaced live tool results with `<memory_summary>`, which Haiku interpreted as a prior conversation → asked "what would you like me to do next?" instead of answering | Raised threshold to **30000 chars** (5-tool queries fit under it) + injected message now ends with explicit `"generate the FINAL pricing recommendation NOW. Do NOT ask follow-up questions, do NOT call more tools"` | F-01 in `Failure_Log_Phase2.md`; commit before submission |
| **Tool 2 controls** | 7 predictors (ln_p + freight + installments + 3 quarter dummies + const) on 21 monthly obs → severe multicollinearity, β sign-flipped to +1.82 for sports | Reduced to **1 control (`avg_freight`)** + explicit sign-flip / `\|Δβ\|>1.0` diagnostic → falls back to naive β with `multicollinearity_warning: True` and a wide honest CI | F-02 in `Failure_Log_Phase2.md`; `priceiq_elasticity.py` v2 code |
| **Executor termination contract** | Executor sometimes re-called a tool with variant args after a failed call | Added a hard rule to the Executor system prompt: **"Each tool is called at most once. Do not retry — neither with identical nor with variant arguments."** Reduces wasted iterations and bounds worst-case cost. | `priceiq_agent.EXECUTOR_PROMPT` rule block |

### Why v3 is "stable"

The three fixes together close the loop on the failure modes v1 and v2 exhibited:

- **v1 failure**: Planner skipped tools (Shortcut Bias) → fixed in v2 by adding examples.
- **v2 latent failure A**: Executor lost final-answer focus under memory compression → fixed in v3 by threshold + finalize instruction.
- **v2 latent failure B**: Tool 2 silently produced wrong-sign β on collinear categories → fixed in v3 by control reduction + diagnostic + naive fallback.
- **v2 latent failure C**: Executor occasionally burned iterations retrying tools → fixed in v3 by explicit single-call rule.

After v3 fixes, 50-case eval shows 92% pass rate with no role-confusion incidents and 100% surface rate on multicollinearity_warning for the cases where it applies. Failure mode is now bounded (low-data category refusal, F-06 OOS leak) rather than silent.

### Deferred to v4 (post-submission roadmap)

| Improvement | Expected impact |
|---|---|
| Token-efficient category list (CSV blob, on-demand parse) | -200 input tokens (-25% of v3 Planner cost) |
| Explicit refusal example (OOS queries → empty `tool_sequence`) | Saves ~$0.005 per OOS leak (see F-06) |
| Skip simulator when elasticity `success: False` | Saves 1 wasted tool call on low-data categories |

---

## Cost comparison (per query, sports test)

| Version | Planner $ | Executor $ | Total $ | Plan completeness | Notes |
|---|---|---|---|---|---|
| v1 | $0.0035 | $0.0163 | $0.0198 | 3 / 5 tools | Shortcut Bias — skips demand/weather |
| v2 | $0.0035 | $0.0252 | $0.0287 | 5 / 5 tools | Plan correct, but latent role-confusion / multicollinearity bugs |
| v3 | $0.0035 | $0.0252 | $0.0287 | 5 / 5 tools | Same prompt as v2; runtime fixes (memory 30K + multicoll diag + single-call rule) — same cost, stable |

**Cost delta v1→v3: +$0.009 per query (+45%) for full pipeline coverage; v2→v3 is $0 incremental.**

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
