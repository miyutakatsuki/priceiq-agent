# Phase 3 — Speaker Notes (5-minute talk)

> One script per slide with timing target. Read out loud once before the live
> session — most lines are written to be **spoken**, not read silently.
>
> Total budget: **5 min = 300 s**. Slide 4 (demo) gets the most time (90 s);
> opening + closing get the least.

---

## Slide 1 — Cover (10 s)

> "Hi, we're team PriceIQ — Kangchun, Tao, and Maoyuan. For the last four
> weeks we built a pricing decision agent on top of 100,000 real Brazilian
> e-commerce orders. I'll walk you through the architecture, one live
> example, and what broke."

*Cue: keep it short, click through fast.*

---

## Slide 2 — The Problem (40 s)

> "Imagine a pricing analyst asks: *should we discount garden tools by 10%
> next month?*
>
> A good answer needs **four kinds of evidence** — and an LLM by itself
> cannot fabricate any of them. On the **quantitative** side, we need a
> price elasticity beta with a confidence interval — measured from real
> data, not guessed. On the **contextual** side, holiday proximity, weather,
> and seasonality each move demand independently.
>
> A single ChatGPT prompt can guess. **A multi-step agent with typed tools
> can compute**. That's why this problem qualifies for the assignment's
> complexity threshold — it's not a chatbot."

*Cue: emphasize "cannot fabricate" — key justification for the agent track.*

---

## Slide 3 — Architecture (45 s)

> "We chose Track B — Claude Agent SDK with a manual `tool_use` loop. The
> assignment requires multi-agent orchestration here, so we split it: a
> **Sonnet 4.5 Planner** does intent parsing and category mapping —
> reasoning-heavy. A **Haiku 4.5 Executor** drives the loop and synthesizes
> the answer — structured-data heavy.
>
> Five typed tools: SQL over Olist, OLS elasticity with a multicollinearity
> diagnostic, demand signals from Brazilian holidays plus seasonality,
> OpenWeather, and a revenue simulator that propagates the beta confidence
> interval into three scenarios.
>
> The hard guardrail is **MAX_ITER equals 8** — the loop cannot drain
> credits. Memory compresses at 30K characters.
>
> The big FinOps win: this Sonnet+Haiku mix gives us **2.9 cents per query**
> — that's 53% cheaper than all-Sonnet, and 22 percentage points more
> accurate than all-Haiku."

*Cue: walk left-to-right on the diagram. Land on the cost number.*

---

## Slide 4 — Live demo (90 s)

> "Here's a real query the agent ran: *should we discount garden tools by
> 10%?*
>
> Five tools fire in 31 seconds. Tool 1 pulls 4,268 orders across 21
> months. Tool 2 fits log-log OLS — beta is **negative 2.83**, highly
> elastic, p less than 0.05, no multicollinearity warning. Tool 3 catches
> Mother's Day eight days out — demand multiplier 1.16. Tool 4 sees rain
> across Brazilian metros — weather drag of 0.94. Tool 5 simulates the
> 10% cut.
>
> The headline: **central scenario is plus 33% revenue**. Pessimistic side
> of the beta CI is plus 21%. Optimistic side is plus 46%. Even the
> pessimistic case beats baseline.
>
> On the right is the actual Streamlit interface — what a real user sees.
> Four recommendation cards, three-scenario chart, and the **causal
> caveat is pasted verbatim** at the bottom. We never let the agent claim
> causation — only directional association.
>
> **Six iterations, 31 seconds, 2.9 cents.**"

*Cue: this is the heart of the talk — slow down, point to specific numbers
on the screenshot. Pause briefly after "central scenario is plus 33%".*

---

## Slide 5 — PVC story (45 s)

> "How do we know the prompt is doing real work? We ran the **same query
> against two prompts**.
>
> Version 1 was under-specified — no examples, no category list, just
> general rules. The Planner only called **3 of 5 tools**. It skipped
> demand and weather entirely. Final answer was directionally correct but
> missing context. We call this **Shortcut Bias** — the LLM takes the
> minimum-effort path the prompt allows.
>
> Version 2 added 5 worked examples and an 11-category whitelist. **All 5
> tools fire**. Plan completes the full pipeline. Cost goes up 45 percent —
> from 2 cents to 2.9 cents — but the answer now cites every driver.
>
> The lesson: **the prompt is not a hint. It's a contract.** Without
> examples, the LLM honors the letter of the spec, not the intent."

*Cue: this is the assignment's PVC requirement. Mention "Shortcut Bias" by
name — it's the failure dissected in the demo video.*

---

## Slide 6 — Evaluation (45 s)

> "We ran a **50-case eval set** — 10 query templates across 5
> categories, plus adversarial prompts. An LLM-as-Judge with a 6-dimension
> rubric scored each run. Three consistency runs per case to measure
> variance.
>
> **92% pass rate** — 46 of 50, average judge score 4.3 out of 5. **2.9
> cents per pass**. **97% category consistency** — Sonnet maps the same
> query to the same Olist category on three independent runs.
>
> Two 100% rates worth flagging: every relevant case surfaces a
> multicollinearity warning, and every successful run includes the causal
> caveat verbatim. These are by-construction guarantees, not statistical
> luck."

*Cue: this slide is dense — point at the donut, then read the two big
numbers, then mention the 100% guarantees in one sentence.*

---

## Slide 7 — Honest failures (30 s)

> "Six failures logged. Four fixed in this phase.
>
> **F-01**: the memory threshold confused the Executor mid-loop — we
> raised it from 8K to 30K and added an explicit *finalize NOW*
> instruction. **F-02**: multicollinearity flipped beta's sign — we cut
> the model from 7 predictors to 2 and added the diagnostic.
>
> **F-06 is open**: an out-of-scope query — *what's the weather in Tokyo* —
> mapped to a Brazilian electronics category instead of refusing. Tool 1's
> *found-False* recovered the run, but it cost half a cent. **Fix is
> deferred to v3** — we documented the failure rather than hide it."

*Cue: tone shift — show humility here. "Documented rather than hid" is
the rubric ask.*

---

## Slide 8 — Q&A (5 s + Q&A time)

> "Repo, demo, eval — all three commands are on the slide. Happy to take
> questions."

*Cue: open palm gesture, step to the side of the screen.*

---

## Timing rehearsal cheat sheet

| # | Slide | Target | Hard cap |
|---|---|---|---|
| 1 | Cover | 10 s | 15 s |
| 2 | Problem | 40 s | 50 s |
| 3 | Architecture | 45 s | 55 s |
| 4 | Demo | 90 s | 100 s |
| 5 | PVC | 45 s | 55 s |
| 6 | Eval | 45 s | 55 s |
| 7 | Failures | 30 s | 40 s |
| 8 | Q&A | 5 s | — |
| **Total** | | **5 min 10 s** | **6 min** |

If you go over on early slides, **cut Slide 6's "two 100% rates" sentence**
— it's the most cuttable detail.

---

## Performance tips

- **Pause after numbers** — "central scenario is plus 33%" — *(beat)* —
  is more memorable than reading straight through.
- **Don't read the slides aloud verbatim**. The audience is faster than
  you. Paraphrase and add the *why*.
- **Hands**: point at the screenshot on slide 4 with an open palm, not a
  finger. Linger 2 seconds on β = −2.83.
- **One tech term per slide, max**. "Multicollinearity" lives on slide 7,
  not slide 4. "Tool_use loop" lives on slide 3, not the cover.
- **Recover from a freeze**: if a slide takes too long to advance, keep
  talking — say "while this loads, the key takeaway is..."
