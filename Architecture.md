# PriceIQ Architecture

> Mermaid diagrams that match the actual code in `priceiq_*.py`.

## Top-level pipeline

```mermaid
flowchart TD
    User([User natural-language<br/>pricing question])
    --> Planner

    subgraph Planner_Agent["Planner Agent (claude-sonnet-4-5)"]
        Planner[XML few-shot prompt v2<br/>71 Olist categories<br/>5 worked examples]
        Plan[(JSON plan:<br/>category_pt +<br/>tool_sequence)]
        Planner --> Plan
    end

    Plan --> Executor

    subgraph Executor_Agent["Executor Agent (claude-haiku-4-5)"]
        Loop[Manual tool_use loop<br/>MAX_ITER=8 kill-switch]
        Mem{history > 30K chars?}
        Compress[Summarize → memory_summary]
        Loop --> Mem
        Mem -->|Yes| Compress
        Compress --> Loop
        Mem -->|No| Loop
    end

    Loop --> T1
    Loop --> T2
    Loop --> T3
    Loop --> T4
    Loop --> T5

    subgraph Tools["5 Tools (pure Python)"]
        T1[Tool 1: query_sales_data<br/>SQL over Olist SQLite<br/>71 categories]
        T2[Tool 2: calculate_price_elasticity<br/>log-log OLS + freight control<br/>multicollinearity diagnostics]
        T3[Tool 3: get_demand_signals<br/>BR holidays + seasonality<br/>α-weighted formula]
        T4[Tool 4: get_weather_signal<br/>OpenWeather 5-day forecast<br/>BR top-5 cities]
        T5[Tool 5: simulate_revenue_impact<br/>3-scenario projection<br/>β CI propagation]
    end

    T1 --> Telemetry
    T2 --> Telemetry
    T3 --> Telemetry
    T4 --> Telemetry
    T5 --> Telemetry

    Telemetry[(Telemetry log:<br/>tokens / latency / errors)]
    --> Final[Final Recommendation<br/>+ causal_caveat<br/>+ multicollinearity warning]
    Final --> User
```

## Tool I/O contracts

```mermaid
flowchart LR
    Cat[category: str] --> T1
    T1[query_sales_data] --> P1[(price_stats<br/>monthly_panel<br/>freight_mean)]

    P1 -->|monthly_panel| T2
    T2[calculate_price_elasticity] --> P2[(elasticity_beta<br/>ci_95<br/>multicollinearity_warning<br/>causal_caveat)]

    Cat --> T3
    T3[get_demand_signals] --> P3[(demand_multiplier<br/>holiday + seasonality<br/>sensitivity_analysis)]

    Cat --> T4
    T4[get_weather_signal] --> P4[(weather_multiplier<br/>rain_prob_5d<br/>temp_anomaly)]

    P2 -->|elasticity| T5
    P3 -->|demand_signal| T5
    P4 -->|weather_signal| T5
    T5[simulate_revenue_impact] --> P5[(3 scenarios:<br/>pessimistic<br/>central<br/>optimistic)]
```

## Sequence: a complete agent run

```mermaid
sequenceDiagram
    actor U as User
    participant Pl as Planner🧠
    participant Ex as Executor⚡
    participant T1 as T1·SQL
    participant T2 as T2·OLS
    participant T3 as T3·Demand
    participant T4 as T4·Weather
    participant T5 as T5·Sim

    U->>Pl: "Discount sports gear 10%?"
    Pl->>Ex: Plan [esporte_lazer · 5 tools]
    Ex->>T1: query_sales_data
    T1-->>Ex: 8431 orders · 21mo panel
    Ex->>T2: calculate_price_elasticity
    T2-->>Ex: β=-1.82 · ⚠ multicollinear
    Ex->>T3: get_demand_signals
    T3-->>Ex: demand=1.12 (Mother's Day)
    Ex->>T4: get_weather_signal
    T4-->>Ex: weather=0.94 (rain)
    Ex->>T5: simulate_revenue_impact(-10%)
    T5-->>Ex: 3 scenarios + CI
    Ex-->>U: Recommendation + causal_caveat
```

## State strategy

```mermaid
stateDiagram-v2
    [*] --> Iteration
    Iteration: Tool-use iteration<br/>(full history retained)
    Iteration --> CheckMem
    CheckMem: history > 30K chars?
    CheckMem --> Iteration: No (continue)
    CheckMem --> Compress: Yes
    Compress: Replace history with<br/>memory_summary block
    Compress --> Iteration
    Iteration --> [*]: stop_reason=end_turn
    Iteration --> KillSwitch: iter == MAX_ITER (8)
    KillSwitch --> [*]: return partial telemetry
```

## Module dependency

See `README.md` § Files for the dependency tree (textual form).
Removed mermaid diagram to avoid duplication — the README ASCII version is
authoritative and updates more naturally with code changes.
