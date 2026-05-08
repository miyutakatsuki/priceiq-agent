"""PriceIQ Agent — Track B (manual tool_use orchestration).

Pipeline:
    User query
       ↓
    Planner (claude-sonnet-4-5)  — XML few-shot prompt v2 with 71-category context
       ↓
    JSON plan {category_pt, tool_sequence, user_intent}
       ↓
    Executor (claude-haiku-4-5)  — manual tool_use loop, MAX_ITER=8 kill-switch
       ↓
    Final answer with verbatim causal_caveat

Hard limits / FinOps:
  MAX_ITERATIONS         = 8     (kill-switch, ADR-003)
  MEMORY_THRESHOLD_CHARS = 30000 (compress history when exceeded; v1 was 8K, see F-01)
  Telemetry              every tool call's input/output/tokens/latency logged

Public API:
    priceiq_agent(user_query, anthropic_client, verbose=True,
                  planner_version='v2') -> dict
        planner_version='v1' reproduces the Shortcut Bias demo failure.
        Returns {success, answer, plan, telemetry}.

Constants:
    TOOLS              — 5-element JSON schema list (Anthropic tool_use format)
    PLANNER_PROMPT_V1  — under-specified (demo-failure prompt)
    PLANNER_PROMPT_V2  — production prompt with 71 categories + 5 few-shots
    EXECUTOR_PROMPT    — synthesizes final answer with verbatim causal_caveat
"""

import json
import time
from typing import Optional


# ── Hard limits ────────────────────────────────────────────────
MAX_ITERATIONS = 8
MEMORY_THRESHOLD_CHARS = 30000   # 5-tool 场景下一般 8-12K，提高阈值避免误触
PLANNER_MODEL = "claude-sonnet-4-5"
EXECUTOR_MODEL = "claude-haiku-4-5"
JUDGE_MODEL = "claude-sonnet-4-5"


# ── TOOLS JSON schema (Anthropic tool_use format) ──────────────
TOOLS = [
    {
        "name": "query_sales_data",
        "description": (
            "Query historical Olist e-commerce sales data for a category. "
            "Returns price stats, freight, and monthly_panel needed for elasticity."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "description": "Olist Portuguese category name (e.g., 'esporte_lazer', 'ferramentas_jardim').",
                },
                "start_date": {"type": "string", "description": "ISO YYYY-MM-DD; optional"},
                "end_date": {"type": "string", "description": "ISO YYYY-MM-DD; optional"},
            },
            "required": ["category"],
        },
    },
    {
        "name": "calculate_price_elasticity",
        "description": (
            "Estimate price elasticity beta via log-log OLS with freight control + "
            "multicollinearity diagnostics. Returns recommended_beta with fallback to "
            "naive when controlled model is unstable. Includes causal_caveat."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "category": {"type": "string"},
                "start_date": {"type": "string"},
                "end_date": {"type": "string"},
            },
            "required": ["category"],
        },
    },
    {
        "name": "get_demand_signals",
        "description": (
            "Combine BR holiday proximity + Olist historical seasonality into a "
            "demand_multiplier. Includes explicit formula and sensitivity_analysis "
            "across alpha_holiday weights."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "category": {"type": "string"},
                "country": {"type": "string", "description": "Default 'BR'"},
            },
            "required": ["category"],
        },
    },
    {
        "name": "get_weather_signal",
        "description": (
            "Fetch real-time 5-day OpenWeather forecast for 5 BR cities, returning "
            "weather_multiplier in [0.80, 1.15]. Only meaningful for sports/garden "
            "categories; auto short-circuits for non-weather-sensitive ones."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "category": {"type": "string"},
                "region": {"type": "string", "description": "Default 'BR'"},
            },
            "required": ["category"],
        },
    },
    {
        "name": "simulate_revenue_impact",
        "description": (
            "Simulate revenue change under a proposed price_change_pct, combining "
            "elasticity beta + demand_mult + weather_mult. Outputs 3 scenarios "
            "(pessimistic/central/optimistic) based on beta's 95% CI."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "category": {"type": "string"},
                "price_change_pct": {
                    "type": "number",
                    "description": "Decimal (-0.10 = -10%, +0.15 = +15%)",
                },
            },
            "required": ["category", "price_change_pct"],
        },
    },
]


def _tool_dispatch(name: str, args: dict) -> dict:
    """把 tool name 派发到本地函数。"""
    if name == "query_sales_data":
        from priceiq_data import query_sales_data
        return query_sales_data(**args)
    if name == "calculate_price_elasticity":
        from priceiq_elasticity import calculate_price_elasticity
        return calculate_price_elasticity(**args)
    if name == "get_demand_signals":
        from priceiq_demand import get_demand_signals
        return get_demand_signals(**args)
    if name == "get_weather_signal":
        from priceiq_weather import get_weather_signal
        return get_weather_signal(**args)
    if name == "simulate_revenue_impact":
        from priceiq_simulator import simulate_revenue_impact
        return simulate_revenue_impact(**args)
    return {"error": f"Unknown tool: {name}"}


# ── Planner Prompt v1 (DELIBERATELY UNDER-SPECIFIED — for PVC log demo) ──
# v1 故意不提供完整 71 类的葡语映射，让 Planner 经常 hallucinate 品类名（如 sports → informatica_acessorios）。
# 这是 demo 视频要剖析的"架构失败"。
PLANNER_PROMPT_V1 = """<context>
You are PriceIQ Planner, an AI that decomposes pricing questions into a tool-call plan.
You have access to 5 tools that work on Brazilian Olist e-commerce data.
</context>

<task>
Given the user's pricing question, output a JSON plan listing which tools to call and in what order.
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
Output ONLY a JSON object:
{
  "category_pt": "<Olist portuguese category>",
  "tool_sequence": ["tool1", "tool2", ...],
  "user_intent": "<one sentence>"
}
</output_format>"""


# ── Planner Prompt v2 (FIXED — adds full category list + few-shot) ────────
# v2 加入完整 71 类 + 5 个 few-shot（含 sports / garden 显式映射）。
PLANNER_PROMPT_V2 = """<context>
You are PriceIQ Planner, an AI that decomposes pricing questions into a tool-call plan.
You have access to 5 tools on Brazilian Olist e-commerce data.

Olist has exactly 71 product categories (Portuguese names). The most common are:
- cama_mesa_banho (bed_bath_table)
- beleza_saude (health_beauty)
- esporte_lazer (sports_leisure)              ← USE FOR ANY "SPORTS" QUERY
- moveis_decoracao (furniture_decor)
- informatica_acessorios (computers_accessories)  ← computers/laptops only
- utilidades_domesticas (housewares)
- relogios_presentes (watches_gifts)
- telefonia (telephony)                       ← phones only
- ferramentas_jardim (garden_tools)           ← USE FOR ANY "GARDEN" QUERY
- automotivo (auto)
- eletronicos (electronics)                   ← TVs/audio only, NOT sports/computers
</context>

<task>
Given the user's pricing question, output a JSON plan listing which tools to call.
</task>

<examples>
Q: "Should we discount sports gear next month?"
A: {"category_pt": "esporte_lazer", "tool_sequence": ["query_sales_data", "calculate_price_elasticity", "get_demand_signals", "get_weather_signal", "simulate_revenue_impact"], "user_intent": "Evaluate impact of discounting sports category"}

Q: "What about a 15% price hike on garden tools?"
A: {"category_pt": "ferramentas_jardim", "tool_sequence": ["query_sales_data", "calculate_price_elasticity", "get_demand_signals", "get_weather_signal", "simulate_revenue_impact"], "user_intent": "Simulate +15% price change on garden tools"}

Q: "How elastic are bed sheets?"
A: {"category_pt": "cama_mesa_banho", "tool_sequence": ["query_sales_data", "calculate_price_elasticity"], "user_intent": "Inquiry about bed_bath_table elasticity (no price change to simulate)"}

Q: "Should we drop laptop prices?"
A: {"category_pt": "informatica_acessorios", "tool_sequence": ["query_sales_data", "calculate_price_elasticity", "get_demand_signals", "simulate_revenue_impact"], "user_intent": "Computer/laptop discount evaluation; weather not relevant"}

Q: "How much should I cut TV prices to clear inventory?"
A: {"category_pt": "eletronicos", "tool_sequence": ["query_sales_data", "calculate_price_elasticity", "get_demand_signals", "simulate_revenue_impact"], "user_intent": "TV/electronics price cut to clear stock"}
</examples>

<rules>
- "sports" / "athletic" / "gym" → esporte_lazer (NOT informatica_acessorios)
- "garden" / "plants" / "tools" → ferramentas_jardim
- weather tool ONLY for sports/garden; skip for others
- Always end with simulate_revenue_impact when a specific Δprice is mentioned
</rules>

<output_format>
Output ONLY a JSON object matching the example schema. No prose.
</output_format>"""


# Default to v2 (production); switch to v1 to reproduce the demo failure
PLANNER_SYSTEM_PROMPT = PLANNER_PROMPT_V2


# ── Executor system prompt ─────────────────────────────────────
EXECUTOR_PROMPT = """<context>
You are PriceIQ Executor. You have a plan from the Planner and 5 tools.
Execute the plan step-by-step using tool_use, gathering structured data.
You have a hard limit of 8 iterations — finalize promptly and do not loop.
</context>

<rules>
- Call tools in the order specified by the plan.
- Pass category_pt (Portuguese) as the category argument to all tools.
- After all tools complete, synthesize a final recommendation that includes:
  1. The recommended beta and its confidence interval
  2. The 3-scenario revenue projection (if simulate was called)
  3. The causal_caveat verbatim from the elasticity tool
  4. The multicollinearity_warning if True
- If a tool returns success=False / found=False, report the failure in your
  final answer and move on. Do not retry the same tool — neither with
  identical nor with variant arguments. Each tool is called at most once.
- Be concise; use bullet points; no prose padding.
</rules>"""


# ── Memory compression ─────────────────────────────────────────
def _compress_memory(messages: list, anthropic_client) -> list:
    """history 太长时，summarize 工具调用历史。"""
    # Anthropic responses contain TextBlock / ToolUseBlock objects (not plain dicts).
    # `default=str` makes json.dumps fall back to repr() for those — see F-04.
    try:
        serialized = json.dumps(messages, default=str)
    except Exception:
        serialized = str(messages)
    if len(serialized) < MEMORY_THRESHOLD_CHARS:
        return messages

    # Compress: ask Haiku to summarize the entire history into 3-5 bullets.
    # Truncate input to 2× the threshold to bound the compress call cost.
    summary = anthropic_client.messages.create(
        model=EXECUTOR_MODEL,
        max_tokens=512,
        system="Summarize this PriceIQ tool execution history into 3-5 bullets focused on key findings (beta, demand_mult, weather_mult, recommended_action). Drop redundant raw data.",
        messages=[{"role": "user", "content": serialized[:MEMORY_THRESHOLD_CHARS * 2]}],
    ).content[0].text

    # Replace history with single user message containing the summary + an
    # explicit "finalize NOW" instruction to prevent role confusion (F-01).
    return [{"role": "user", "content": (
        f"<memory_summary>\n{summary}\n</memory_summary>\n\n"
        "Based on the above tool results summarized in memory, generate the FINAL "
        "pricing recommendation NOW. Do NOT ask follow-up questions, do NOT call "
        "more tools. Synthesize the recommendation with: (1) recommended beta + CI, "
        "(2) 3-scenario revenue projection, (3) causal_caveat, (4) multicollinearity "
        "warning if any."
    )}]


# ── Main agent entry point ─────────────────────────────────────
def priceiq_agent(user_query: str, anthropic_client, verbose: bool = True,
                  planner_version: str = "v2") -> dict:
    """Run the full Planner → Executor pipeline.

    Args:
        user_query:        Natural-language pricing question.
        anthropic_client:  `anthropic.Anthropic()` instance.
        verbose:           Print iteration progress to stdout.
        planner_version:   'v2' (production) | 'v1' (Shortcut Bias demo).

    Returns:
        {
          "success":   bool,
          "answer":    str,            # final Executor synthesis
          "plan":      dict,           # {category_pt, tool_sequence, user_intent}
          "telemetry": {
              "query":            str,
              "planner_version":  str,
              "planner_tokens":   {input, output},
              "executor_tokens":  [{iter, input, output}, …],
              "tool_calls":       [{iter, tool, input, latency_s, error, result_keys}, …],
              "errors":           [{iter, tool, err}, …],   # per-tool errors during execution
              "iterations":       int,
              "latency_s":        float,
              "started_at":       float,
              "finished_at":      float,
              "plan":             dict,                      # echo of Planner output
              "final_answer":     str,                       # only when success=True
              "error":            str,                       # only when success=False (e.g. MAX_ITER hit)
          }
        }
    """
    prompt = PLANNER_PROMPT_V1 if planner_version == "v1" else PLANNER_PROMPT_V2
    telemetry = {"query": user_query, "planner_version": planner_version,
                 "started_at": time.time(), "tool_calls": [], "errors": []}

    # ── Planner ────────────────────────────────────────────
    if verbose:
        print(f"\n[Planner {planner_version}] {PLANNER_MODEL}")
    plan_resp = anthropic_client.messages.create(
        model=PLANNER_MODEL,
        max_tokens=512,
        system=prompt,
        messages=[{"role": "user", "content": user_query}],
    )
    plan_text = plan_resp.content[0].text.strip()
    telemetry["planner_tokens"] = {
        "input": plan_resp.usage.input_tokens,
        "output": plan_resp.usage.output_tokens,
    }
    try:
        plan = json.loads(plan_text)
    except json.JSONDecodeError:
        # 抽取第一个 {...}
        import re
        m = re.search(r"\{.*\}", plan_text, re.DOTALL)
        plan = json.loads(m.group(0)) if m else {"error": "plan_parse_failed", "raw": plan_text}
    if verbose:
        print(f"[Plan] {plan}")
    telemetry["plan"] = plan

    if "category_pt" not in plan:
        return {"success": False, "telemetry": telemetry,
                "error": "Planner failed to produce category_pt"}

    # ── Executor (manual tool_use loop) ─────────────────────
    if verbose:
        print(f"\n[Executor] {EXECUTOR_MODEL}")

    enriched_query = (
        f"User question: {user_query}\n\n"
        f"Plan from Planner:\n{json.dumps(plan, indent=2)}\n\n"
        f"Execute the tool_sequence in order. Use category_pt='{plan['category_pt']}' for all category arguments."
    )
    messages = [{"role": "user", "content": enriched_query}]

    for iteration in range(MAX_ITERATIONS):
        if verbose:
            print(f"  [iter {iteration+1}/{MAX_ITERATIONS}]")

        # Memory 压缩
        messages = _compress_memory(messages, anthropic_client)

        resp = anthropic_client.messages.create(
            model=EXECUTOR_MODEL,
            max_tokens=2048,
            system=EXECUTOR_PROMPT,
            tools=TOOLS,
            messages=messages,
        )
        telemetry.setdefault("executor_tokens", []).append({
            "iter": iteration + 1,
            "input": resp.usage.input_tokens,
            "output": resp.usage.output_tokens,
        })

        # 把 assistant 回应加进 history
        messages.append({"role": "assistant", "content": resp.content})

        if resp.stop_reason == "end_turn":
            # Final answer
            final_text = "".join(b.text for b in resp.content if hasattr(b, "text"))
            telemetry["final_answer"] = final_text
            telemetry["finished_at"] = time.time()
            telemetry["latency_s"] = telemetry["finished_at"] - telemetry["started_at"]
            telemetry["iterations"] = iteration + 1
            return {"success": True, "answer": final_text, "plan": plan, "telemetry": telemetry}

        if resp.stop_reason == "tool_use":
            tool_results = []
            for block in resp.content:
                if block.type == "tool_use":
                    name, inp = block.name, block.input
                    if verbose:
                        print(f"    [tool_use] {name}({inp})")
                    t0 = time.time()
                    try:
                        result = _tool_dispatch(name, inp)
                        err = None
                    except Exception as e:
                        result = {"error": str(e)}
                        err = str(e)
                        telemetry["errors"].append({"iter": iteration+1, "tool": name, "err": err})
                    latency = time.time() - t0
                    telemetry["tool_calls"].append({
                        "iter": iteration + 1,
                        "tool": name,
                        "input": inp,
                        "latency_s": round(latency, 3),
                        "error": err,
                        "result_keys": list(result.keys()) if isinstance(result, dict) else None,
                    })
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": json.dumps(result)[:8000],
                    })
            messages.append({"role": "user", "content": tool_results})

    # MAX_ITER hit
    telemetry["error"] = f"Hit MAX_ITERATIONS={MAX_ITERATIONS} without end_turn"
    telemetry["finished_at"] = time.time()
    return {"success": False, "telemetry": telemetry,
            "answer": "Agent exceeded iteration cap; partial results in telemetry."}
