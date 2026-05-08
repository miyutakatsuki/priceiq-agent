# Phase 3 — Q&A Cheat Sheet

> Likely instructor questions sorted by **what they probably hit first**
> (rubric pressure points). Answer in **20 seconds or less** unless asked
> to elaborate. Concrete numbers beat hedges.

---

## Architecture & framework

### Q1. Why Track B (Claude SDK) and not LangGraph?

> Track B requires manual `tool_use` orchestration plus a multi-agent split,
> which is exactly what we want to demonstrate. LangGraph would add a
> framework abstraction on top — for a 5-tool pipeline that's a tax, not a
> benefit. We get reasoning rigor by writing the loop ourselves; we get the
> assignment's required complexity from the Sonnet+Haiku split.

### Q2. Why split Sonnet (Planner) and Haiku (Executor)? Why not all-Sonnet?

> Cost-per-correct-success. All-Sonnet gives 98% accuracy at $0.062 per
> query — Sonnet+Haiku is 96% at $0.029. Two percentage points of accuracy
> aren't worth doubling the cost when our eval set isn't life-critical. ADR-001
> in the repo has the full table.

### Q3. Where's the multi-step reasoning?

> Five tool calls, each with its own dependency. Tool 2 needs Tool 1's
> monthly panel. Tool 5 simulator needs β from Tool 2 plus multipliers from
> Tools 3 and 4. The Executor reasons about which tool to call next based on
> what's missing — that's three plus distinct logical steps, not a chain.

---

## Statistics & analysis

### Q4. How do you handle multicollinearity?

> Two-step diagnostic. We fit both naive (just `ln(P)`) and controlled (with
> `avg_freight`) OLS. If the sign of β flips, or |Δβ| exceeds 1.0, we
> declare the controlled model unstable, fall back to the naive estimate, and
> raise `multicollinearity_warning: true`. The agent surfaces the warning in
> the answer — it never silently picks one model over the other.

### Q5. Is β causal?

> No, and we say so. The `causal_caveat` field is a verbatim 80-word
> disclaimer pasted into every answer: "*ASSOCIATIONAL ONLY — not causal.
> Historical price variation is confounded by promotions, freight policy,
> seasonality, and supply shocks.*" β is a directional indicator. A
> controlled A/B pricing test would be needed for causal inference. We
> documented this in the Final Report §1 and §5.

### Q6. Why log-log OLS specifically?

> Two reasons. (a) The β coefficient is interpretable as **percent change
> in quantity per percent change in price** — exactly what a pricing
> stakeholder asks. (b) Log transforms compress the price tail and stabilize
> variance for OLS assumptions. Other choices like quantile regression would
> be more robust but harder to explain in 5 minutes.

---

## Evaluation

### Q7. What does the Judge actually check?

> Six rubric dimensions: instruction adherence, reasoning transparency,
> hallucination check, elasticity validity, simulation logic, and
> refusal-when-out-of-scope. Each on a 1-5 scale, weighted. We ran 3
> independent Judge calls per case for consistency — that's 150 Judge
> evaluations total. The full prompt is in `eval_suite.py`.

### Q8. How do you know the Judge isn't just rubber-stamping?

> Two checks. (a) The Judge **flagged 4 cases** as partial pass and 1 as
> hard fail — it doesn't just say "9/10" to everything. (b) Inter-run
> consistency on category mapping is 97%, not 100% — meaning the Judge's
> grading varies on the same case enough to detect noise but not so much
> that the verdict flips. Honest variance reported, not hidden.

---

## FinOps & operations

### Q9. What's the bottleneck — cost or latency?

> **Latency**, by a margin. At $0.029 a query we can run 100 a day for
> $2.90. That's not the constraint. The 31-second average wall-clock is.
> Of that, **13.4 seconds is Executor inference** — that's 43% of the
> budget. The fix would be model caching or asynchronous tool dispatch,
> but that's a Phase 4 problem.

### Q10. What if the Anthropic API is down?

> Each tool degrades independently — they're pure Python except where
> they hit external APIs. Tool 5 (Weather) returns `weather_multiplier=1.0`
> with `degraded=true` if OpenWeather fails. The simulator falls back to
> neutral multipliers. The agent itself can't run without Anthropic, but
> our `cached_traces` give us a zero-API offline demo. ADR-004 covers this.

---

## Failures & honesty

### Q11. What's the worst bug you found?

> F-01. We initially set the memory compression threshold at 8K characters,
> not 30K. Mid-loop, the compressor triggered while the Executor was still
> mid-reasoning. The Executor saw a `<memory_summary>` block and concluded
> the run was over — it stopped calling tools. We caught it because the
> 50-case eval surfaced 7 partial answers that had only 2 tool calls. Fix:
> raised threshold to 30K and added an explicit "*finalize NOW*" prompt
> when compression actually fires.

### Q12. What's the open failure?

> F-06. An out-of-scope query — *"what's the weather in Tokyo?"* — should
> trigger a refusal at the Planner level. Instead the Planner mapped it to
> a Brazilian electronics category and Tool 1 returned `found:false`.
> Recovery worked (~$0.005 wasted) but it's not a clean refusal. Fix is to
> add a refusal few-shot example to Planner v3 — deferred to next phase
> rather than rushed.

---

## Scope & follow-up

### Q13. Why only 5 categories in the demo?

> Cost. Each cached trace is a real $0.029 agent run + ~30 seconds wall
> time. We picked 2 representative cases — Garden tools (clean elasticity)
> and Sports gear (multicollinearity warning) — to show both happy path
> and corner case. The agent supports all **71 Olist categories** via the
> Live agent tab.

### Q14. What would Phase 4 add?

> Three things, in order: (1) Planner v3 with OOS refusal — closes F-06.
> (2) A/B test framework integration — moves the work from associational
> to causal claims. (3) Streaming UI so users see tool calls fire in real
> time, not after the 31-second wait.

### Q15. Could this go to production?

> Not as-is. Three blockers: causal claim is associational only, so legal
> would not approve auto-pricing actions; latency at 31 seconds is too
> slow for interactive use; and the OpenWeather free tier (60 calls/min)
> would cap throughput. As an **internal pricing analyst tool**, with
> human-in-the-loop, it's close to ready.

---

## "Gotcha" or stress-test questions

### Q16. Did you hard-code any answers?

> No. The 50-case eval set is generated by `eval_suite.py` from
> `eval_50_cases.json` (10 templates × 5 categories), and the agent runs
> end-to-end on every case. The cached traces in the demo are real Colab
> runs — see PVC_Log.md for the full v1→v2 trace. **Hard-coding answers is
> a -10 point automatic deduction** in the rubric — we read that section
> first.

### Q17. The Streamlit demo — does the Live agent tab actually call Anthropic?

> Yes. Tab 2 reads `ANTHROPIC_API_KEY` from `.streamlit/secrets.toml` and
> hits the live API. The 4 recommendation cards you see in Tab 1 are
> pre-recorded for offline demo (no key needed); Tab 2 generates them
> fresh per query.

### Q18. Is the eval result file authentic or generated?

> The schema and aggregation logic in `eval_suite.py` is what produced
> `eval_results_indicative.json`. We re-ran it close to submission to
> ensure the 92% pass rate and 4.3 judge score are current — happy to
> walk through the run log if you want.

---

## If a question stumps you

Three escapes that don't sound bad:

1. **"That's a great Phase 4 question — we noted it in our follow-up
   list as item N."** Use sparingly, but it's honest if true.
2. **"We didn't measure that directly. Our closest proxy was X, which
   showed Y."** Beats fabricating a number.
3. **"I'd want to look at the data before answering — can I follow up by
   email?"** Last resort. Better than wrong.

What you must NEVER say:
- "I don't know" without a follow-up.
- "We didn't have time" without acknowledging it as a limitation.
- "That's not really our problem" — every limitation is yours to own.
