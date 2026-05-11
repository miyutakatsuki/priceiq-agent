# Architecture Decision Records — PriceIQ Phase 2

> Per assignment: "For each major component, you must provide an Architecture
> Decision Record." Four ADRs covering Model Selection, AI vs Rule-Based,
> State Strategy, Error Handling.

## Index

| # | Decision | Status |
|---|---|---|
| ADR-001 | Model Selection — Sonnet (Planner) + Haiku (Executor) | Accepted |
| ADR-002 | AI vs Rule-Based — what's an LLM, what's a function? | Accepted |
| ADR-003 | State Strategy — full history + 30K-char compression fallback | Accepted (revised) |
| ADR-004 | Error Handling — graceful degradation over crash-stop | Accepted |

> Status legend: **Accepted** = currently in production. **Accepted (revised)** =
> originally accepted, parameters tuned later (see ADR for trace). **Superseded**
> = replaced by a later ADR (none yet at submission).

---

## ADR-001: Model Selection — Sonnet (Planner) + Haiku (Executor)

**Status**: Accepted · 2026-04-19 (initial) · 2026-05-07 (validated)

### Context
Track B requires Multi-Agent Orchestration. Two LLM roles: **Planner** (parse
intent, English→Portuguese mapping, decide tool sequence — reasoning-heavy)
and **Executor** (drive tool_use loop, parse results, synthesize answer —
high-volume, procedural).

### Options considered
| Option | Reasoning | Cost / 1M tok | Latency |
|---|---|---|---|
| A. Sonnet for both | Max reasoning quality | $3 in / $15 out | Higher |
| **B. Sonnet → Haiku (chosen)** | Reason once, execute cheaply | Mixed | Lower |
| C. Haiku for both | Cheapest | $1 in / $5 out | Lowest |

### Decision
**Sonnet 4.5 for Planner, Haiku 4.5 for Executor.**

### Rationale
Planner is called **1×/query** but gates everything downstream — wrong plan ⇒ wasted
Executor calls. Sonnet's marginal $0.0035 is worth it. Executor is called **6×/query**
reading heavy tool results; Haiku at 1/3 cost handles structured-data synthesis since
reasoning is already encoded in the plan.

### Validation (Phase 2 eval, n=50)
| Config | Cost / success | Pass rate | Cost / **correct** success |
|---|---|---|---|
| A. Sonnet+Sonnet | $0.061 | 98% | $0.062 |
| **B. Sonnet+Haiku (chosen)** | **$0.029** | **96%** | **$0.030** |
| C. Haiku+Haiku | $0.012 | 76% | $0.016 |

B wins on effective cost once accuracy is factored.

### Consequences
- ✅ ~50% cost reduction vs all-Sonnet
- ✅ Prompt-engineering effort concentrated on Planner only
- ⚠️ Two model versions to pin — mitigated via explicit constants in `priceiq_agent.py`

---

## ADR-002: AI vs Rule-Based — what's an LLM, what's a function?

**Status**: Accepted · 2026-05-07

> **Rule of thumb**: LLM only where natural-language ambiguity, intent parsing, or
> fluent synthesis is needed. Pure Python for everything with a closed-form
> mathematical or calendar answer.

### Context
The assignment requires explicit justification for LLM-vs-`if/else` choices.
Seven decisions, summarized below.

### Alternatives considered (and why rejected)

| Approach | Why we didn't choose it |
|---|---|
| **All-LLM** (let Executor pick categories AND do math via tool descriptions only) | Numerical hallucination risk: free-form Sonnet/Haiku math drifts ~5-15% per run, killing the rigor required for `β` estimates. Audit failure for any pricing decision. |
| **All-rules** (deterministic intent parser + fixed tool chain) | 71 Olist categories × N English/Portuguese synonyms × ambiguous queries ("the bedding stuff") are not tractable as regex. Rejected after Phase 1 prototype showed 60% misclassification on adversarial inputs. |
| **LLM only for synthesis** (Planner+Executor as glue; tools called rigidly) | Defeats the point of multi-agent orchestration — degenerates into a templated RAG pipeline. Fails rubric §2 Gatekeeper ("Ambiguity Resolution"). |
| **Hybrid by domain** (chosen, see table) | LLM where ambiguity / synthesis is fundamental; deterministic code where the answer has a closed form. Best of both. |

### Decisions table

| Component | Choice | Why | Risk if wrong |
|---|---|---|---|
| English→Portuguese category mapping | **LLM** (Planner) | 71 cats × N synonyms + ambiguity — hard-coding is brittle | Wrong category → wrong recommendation |
| Tool sequencing | **LLM** (Planner) | Real queries are messy ("cut prices only if demand is up") | Skipped tool → Shortcut Bias (PVC v1) |
| Holiday proximity | **Code** (`_holiday_signal`) | Pure calendar arithmetic; determinism matters | Audit failure if dates shift |
| OLS with controls | **Code** (`statsmodels.OLS`) | Statistical rigor needs reproducible numerics | β values drift with LLM "reasoning" |
| Multicollinearity check | **Code** (sign-flip + \|Δβ\|>1.0) | Small well-defined rule | Latency tax for zero benefit |
| Causal caveat | **Hybrid** | Constant string + LLM quotes in answer | Compliance text drift if LLM edits |
| Final prose | **LLM** (Executor) | Stakeholder-facing text needs natural language | Robotic output if Code-templated |

### Rationale
We use LLMs only where natural-language ambiguity, intent parsing, or fluent
synthesis is required. Everything with a closed-form mathematical or calendar
answer is pure Python. This minimizes hallucination surface area and keeps
auditable parts auditable.

### Consequences
- ✅ Numerical claims are reproducible (β, CI, revenue deterministic given snapshot)
- ✅ Smaller LLM context per call (no math reasoning in tokens)
- ⚠️ The English↔Portuguese category seam is the highest-risk coupling — mitigated by Sonnet (ADR-001) + PVC v2 few-shot examples

---

## ADR-003: State Strategy — Full history with 30K-char compression fallback

**Status**: Accepted · 2026-05-07 (revised from 8K → 30K threshold after F-01)

### Context
Anthropic tool_use history grows fast: each iteration adds an assistant message
(with `tool_use` blocks) + a user `tool_result` block. `simulate_revenue_impact`
alone returns ~3KB JSON; 5 tools × 1–3KB ≈ 8–15KB per iteration. Naive full
history hits Haiku's context cap after ~20 iterations.

### Options considered
| Option | Pros | Cons |
|---|---|---|
| A. Full history, no compression | Simple, lossless | Hits context cap on long runs |
| B. Aggressive summarization (every iteration) | Always small | Loss of detail; agent confused |
| C. **Threshold-triggered compression (chosen)** | Compress only when needed | Initial threshold tuning required |
| D. Keep last N messages, drop oldest | Constant memory | Drops critical first tool call (sales data) |

### Decision
**Threshold-triggered compression**:
- Trigger: serialized history > 30,000 chars
- Action: summarize entire history to 3–5 bullets, replace with single
  `<memory_summary>...</memory_summary>` user message + explicit "generate FINAL
  recommendation now" instruction
- Threshold value evolved: 8K (v1) → 30K (v2) after empirical bug

### v1 → v2 evolution (Phase 2 finding)
**v1 (8K threshold)**: hit mid-loop on 5-tool queries → Executor saw the summary
as a *prior conversation*, asked "what would you like me to do next?" and
**never produced a final answer**.

**v2 (30K threshold + explicit instruction)**: 5-tool queries fit under the
threshold; compression only fires on edge cases (7+ tool retries). Injected
summary now ends with "generate FINAL recommendation NOW, do NOT ask follow-up"
to prevent role confusion.

### Consequences
- ✅ Simple invariant: queries under 30K cumulative history are bit-for-bit reproducible
- ✅ Compression path is exercised in evaluation edge cases — not dead code
- ⚠️ Compression *does* lose information; telemetry sets `compression_fired: true`, those traces are disqualified from accuracy metrics

### Companion guardrails (rubric §4B: iterations AND token-spend caps)

State strategy alone is insufficient — three hard caps prevent runaway cost:

| Constant | Value | What it bounds |
|---|---|---|
| `MAX_ITERATIONS` | 8 | Executor loop iterations (rubric range 5–10) |
| `MAX_PLANNER_TOKENS` | 5,000 | Single Planner call (~5× nominal v2 of 930); guards against prompt injection / pathological category strings |
| `MAX_EXECUTOR_TOKENS` | 80,000 | Cumulative input+output across all Executor calls per query (~4× nominal 18K); guards against retry-storms and verbose intermediate output |

All three are enforced with explicit return paths that produce a `success: False`
result with `"answer": "..."` (graceful, not exception). Telemetry records the
exact value at trip time, so post-mortems can distinguish iteration cap hits from
token cap hits from clean end_turn.

---

## ADR-004: Error Handling — Graceful degradation per tool

**Status**: Accepted · 2026-04-19 (Phase 1, refined Phase 2)

### Context
We have 5 tools, each with different failure modes:
- Tool 1 (SQL): Olist DB unavailable, category not found, or empty result set
- Tool 2 (OLS): Insufficient panel data (< 8 months), multicollinearity instability
- Tool 3 (Demand): Calendar arithmetic errors, missing month in pattern
- Tool 4 (Weather): OpenWeather API timeout, rate limit, key not yet activated
- Tool 5 (Simulator): Upstream failure cascade

Hard failures cascade: if Tool 2 throws, Tool 5 has no β to use. We need a
contract that lets the Executor make sense of partial failures.

### Options considered

| Option | Pros | Cons | Rejected because |
|---|---|---|---|
| A. Tools raise; Executor `try/except` per call | Pythonic, lets you log stack traces | Adds 5× try/except boilerplate in Executor; exception type is leaky abstraction; Anthropic's `tool_use` protocol expects `tool_result` content, not Python exceptions | High cost for low signal — and `tool_use` already wraps results in a content block |
| B. Tools return `Either[T, error]` style monad | Type-safe, composable | Python lacks language-level support; readers unfamiliar with FP get lost; serializing to JSON for tool_result requires unwrapping anyway | Idiomatic Python idea would be too clever |
| C. Tools return None on failure | Minimal change | LLM Executor can't distinguish "no data" from "tool broken"; loses the reason | Information loss |
| **D. Tools always return `dict` with status field** (chosen) | Structured, JSON-native, self-documenting; Executor sees same shape on success and failure; reasons preserved | Tools must remember to honor the contract (linter could enforce, manual today) | None — this is the chosen path |

### Decision
Every tool **always returns a structured dict, never raises** — with a required
status field (`success` / `found` / `applicable`) and a `message` reason on failure.

### Per-tool degradation policy
| Tool | Failure mode | Degradation |
|---|---|---|
| 1 SQL | Category not found | `{found: False, message}` — Executor reports back |
| 1 SQL | DB download failed | Raise (infra error, caught in agent loop) |
| 2 OLS | n < 8 months | `{success: False}` with reason — Executor honest |
| 2 OLS | Multicollinearity | `multicollinearity_warning: True` + naive-β fallback — does not fail |
| 3 Demand | Insufficient monthly data | `seasonality_multiplier: 1.0`, holiday still computed |
| 4 Weather | API timeout / inactive key | `{degraded: True, weather_multiplier: 1.0}` |
| 4 Weather | Non-sports/garden | `{applicable: False, weather_multiplier: 1.0}` — short-circuit |
| 5 Sim | Upstream Tool 2 failed | `{success: False, message}` — no retry with bad inputs |

### Telemetry contract
The agent records every tool call's `error` field. Successful runs have
`error: None` for all 5 tools. Degraded runs have non-None error fields and
the final answer notes the degradation.

### Rationale
A partially-answering agent beats a silently-500ing one. Low-data category →
"insufficient data", not "internal error". Weather API hiccup shouldn't nuke
the whole revenue simulation.

### Consequences
- ✅ 50-case eval includes deliberate failures (made-up category, invalid key) — all return informative answers, none crash
- ✅ Causal caveat always emitted (Tool 2's structured output is always parseable)
- ⚠️ Executor must *report* `success: False` rather than retry — handled by EXECUTOR_PROMPT rules
