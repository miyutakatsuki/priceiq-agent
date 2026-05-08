# PriceIQ Demo Video Storyboard — 5 minutes

> **Per assignment**: "5-minute deep-dive into ONE specific architectural failure
> and how you solved it." Topic: **Shortcut Bias in under-specified Planner prompts**.

**Recording stack**: QuickTime Player screen recording on macOS, 1080p.
**Voiceover**: Recorded in one take after rehearsal.
**Output**: YouTube unlisted link.

---

## Beat sheet

| Time | Beat | Visual | Voiceover (English) |
|---|---|---|---|
| 0:00–0:25 | **Hook + project tagline** | Streamlit landing page (PriceIQ logo + Mermaid arch on screen) | "PriceIQ is a Track B Claude SDK agent that turns natural-language pricing questions into Olist-grounded recommendations. Today I'll show you the one architectural failure we found, why we missed it on first design, and the fix." |
| 0:25–1:00 | **Architecture in 30s** | Mermaid diagram: User → Planner (Sonnet) → Executor (Haiku) → 5 Tools → Recommendation | "Two-agent setup. Planner reads the question and outputs a JSON tool plan. Executor runs that plan in a manual tool_use loop, capped at 8 iterations. Five tools: SQL on Olist, log-log regression, demand signals, weather, revenue simulator." |
| 1:00–2:00 | **The failure (live)** | PPT slide 5 (PVC story): two columns showing v1 chips (3 active, 2 dim) vs v2 chips (5 active) for "Should we discount sports gear by 10%?" | "Watch this. Same query, v1 on the left, v2 on the right. v1's plan has only 3 tools — SQL, OLS, simulator. v2's plan has all 5, adding demand and weather. The agent succeeds either way — but v1's answer is missing the demand and weather context. We call this Shortcut Bias: the LLM took the minimum-effort path because nothing in the prompt insisted otherwise." |
| 2:00–2:45 | **Why this matters** | PVC_Log.md scrolled to v1 vs v2 final answer comparison | "v1 says: discount viable, revenue −29 to +66 percent — very wide CI. v2 says: revenue −24 to +76, with demand tailwind from Mother's Day, May seasonality, partially offset by rain headwind. Same direction, but the v1 simulator defaulted demand and weather to 1.0 — so a stakeholder reading v1 has no idea those drivers even exist." |
| 2:45–3:30 | **The diagnosis** | Code view of v1 prompt (highlighted) → v2 prompt (highlighted diff) | "v1 had general rules with no examples. Sonnet inferred the most likely 3 tools from the rules and stopped. The fix in v2: five concrete few-shot examples, each showing the *complete* 5-tool sequence, plus negative examples: 'sports → esporte_lazer, NOT informatica_acessorios.' The prompt grew from 200 tokens to 825 tokens. That's a 45% cost increase per Planner call." |
| 3:30–4:15 | **Validation** | Streamlit Live agent tab — run the v2 query end-to-end, show all 5 tool_use blocks streaming | "Re-run with v2. Plan: 5 tools. Iteration 1: query_sales_data. Iteration 2: elasticity, beta minus 1.8, multicollinearity warning correctly flagged. Iteration 3: demand signals, multiplier 1.12. Iteration 4: weather, multiplier 0.94. Iteration 5: simulator, three scenarios. Total 30 seconds, $0.029. Final answer now cites all four drivers." |
| 4:15–4:45 | **What we learned (generalizable)** | Bullet list overlay | "Three lessons. One: list your domain entities explicitly — Sonnet can infer Portuguese, but it can't infer 'these signals matter' without being told. Two: few-shot examples must show the *complete* desired behavior, not just syntax. Three: honest post-mortems beat dramatic fictional failures. We expected sports-to-laptops misclassification. We got tool-skipping. The real bug was more interesting." |
| 4:45–5:00 | **Close** | Streamlit final scenario chart visible | "PriceIQ. Planner-Executor with manual tool_use. Olist-grounded. Causal disclaimers everywhere they belong. Thanks." |

---

## Recording checklist

- [ ] Clean Chrome (one tab: `localhost:8501`); DevTools closed; no keys visible
- [ ] `streamlit run app.py` running; cached traces pre-loaded for instant PVC render
- [ ] 30s mic test recording first
- [ ] Captions pre-written from this storyboard

## Post-production cuts

- 0:25 fade to architecture diagram
- 2:00 split-screen freeze on Final Answer diff
- 3:30 zoom on v2 prompt diff (strike-through missing examples in red)
- 4:15 callout boxes per tool name as it streams

## Risk mitigations

| Risk | Mitigation |
|---|---|
| Live agent call fails mid-recording | Cached tab is primary; live tab is "extra credit" |
| Voiceover too fast | ~370 words across 5:00 = 74 wpm — readable but tight; rehearse pacing once |
| API key visible | `st.secrets` reads from `.streamlit/secrets.toml`, never on screen |
| Demo runs over 5 min | Beats 4:15 / 4:45 are compressible; cut to 4:30 close |
| Streamlit hot-reload mid-record | Disable `runOnSave` in `.streamlit/config.toml` before recording |

---

## Submission checklist (Phase 2)

- [ ] YouTube unlisted upload
- [ ] Description includes: 1-line summary, link to GitHub repo, link to Phase 2 report PDF
- [ ] Captions enabled (auto-gen acceptable, manual preferred)
- [ ] Thumbnail: Streamlit landing screenshot
