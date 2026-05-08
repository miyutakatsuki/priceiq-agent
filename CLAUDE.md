# CLAUDE.md — PriceIQ Agent Project

> 用途：项目级操作指南。新会话开始时直接读这份文件，不需要让用户重新解释背景。
> 当前阶段：**Phase 2 已交付，Phase 3（现场 presentation）准备中**
> Repo：https://github.com/miyutakatsuki/priceiq-agent

---

## 用户偏好（必须遵守）

- **语言**：默认中文回复，专业术语保留英文原文
- **作业答案生成时**：用英文
- **回复原则**：结论前置、不说废话、不确定就说不确定、欢迎被反驳
- **格式**：短问题→简短回答无列表；复杂问题→结构化；代码→完整可运行+简短注释
- **CLAUDE.md 维护**：被动模式 — 只在用户明确要求时更新；不要自动 sync 状态变化

---

## 项目一句话

输入自然语言定价问题 → Planner（Sonnet）+ Executor（Haiku）双 agent → 调 5 个工具 → 输出基于 Olist 真实数据的弹性估计 + 3 场景收益模拟 + 必带 causal caveat。

---

## 课程信息

- **课程**：Generative AI（JHU Carey 商学院，2026 春）
- **团队**：Kangchun Sun · Tao Cheng · Maoyuan Li
- **Track B**：Claude Agent SDK，手写 `tool_use` loop，Planner + Executor 多 agent（不用 Managed Agents）

| 阶段 | 截止 | 占分 | 状态 |
|---|---|---|---|
| Phase 1 — 提案 + prototype | Week 5 | 30% | ✅ 已提交 |
| Phase 2 — 代码 + 报告 + demo 视频 | Week 8 | 50% | ✅ 代码 + 报告完成；🟡 demo 视频用户自录 |
| Phase 3 — 5 min 现场 presentation + Q&A | Week 8 | 20% | 🟡 slides + 演讲稿 + QA cheatsheet 完成；待练习 |

---

## 技术架构（5 工具版，Phase 2 实施）

```
User query (NL)
      ↓
Planner — claude-sonnet-4-5 — XML few-shot prompt v2
      ↓ JSON plan
Executor — claude-haiku-4-5 — manual tool_use loop, MAX_ITER=8
      ↓
[Tool 1] query_sales_data        Olist SQLite, ~100K orders, 71 categories
[Tool 2] calculate_price_elasticity  log-log OLS + multicollinearity diagnostic
[Tool 3] get_demand_signals      BR holidays + 22-mo seasonality, α-weighted formula
[Tool 4] get_weather_signal      OpenWeather 5-day, BR top-5 cities (sports/garden only)
[Tool 5] simulate_revenue_impact  3 scenarios from β CI propagation
      ↓
Final answer + verbatim causal_caveat
```

## 安全机制

- **Kill switch**：`MAX_ITERATIONS = 8`
- **Memory compression**：history serialized > 30K chars → summarize（threshold 升过，原 8K 触发 F-01）
- **Graceful degradation**：每个 tool 独立 fail，weather→1.0 mult, demand→neutral
- **Multicollinearity guard**：sign-flip 或 |Δβ|>1.0 → naive fallback + 公开 warning
- **Causal caveat**：每个成功 run 都 paste verbatim associational-only 80-word 免责
- **API keys**：仅 env / `.streamlit/secrets.toml` 读，源码无明文（已 grep 验证）

## No-Go Zone（rubric 自动扣分）

- **-10 分**：用 Claude.ai 网页 UI 做 demo
- **-10 分**：Hard-code 测试答案
- **-5 分**：API key 出现在代码或报告里

---

## 关键文件 quick-ref

**Core agent (`priceiq_*.py`)**
- `priceiq_agent.py` — TOOLS schema · Planner v1/v2 · Executor loop · telemetry
- `priceiq_data.py` — Tool 1 SQL
- `priceiq_elasticity.py` — Tool 2 OLS + multicollinearity
- `priceiq_demand.py` — Tool 3 holidays + seasonality
- `priceiq_simulator.py` — Tool 4 revenue projection
- `priceiq_weather.py` — Tool 5 OpenWeather

**Demo + eval**
- `app.py` — Streamlit UI（Cached demo + Live agent，light theme，v0.dev 风）
- `cached_traces.py` — 3 个真实 agent runs（GARDEN, SPORTS, SPORTS_V1）
- `eval_suite.py` — 50 cases generator + LLM-as-Judge + consistency runner
- `eval_50_cases.json` — 50 test queries
- `eval_results_indicative.json` — ⚠️ 标 disclaimer 是 extrapolated。final submission 前需跑 `run_eval.py` 替换为 canonical
- `run_eval.py` — 一键替换 indicative → real (~$2.57, ~25 min)

**Phase 2 deliverable docs (`*.md`)**
- `Phase2_Final_Report.md` · `PVC_Log.md` · `ADRs.md` · `Architecture.md`
- `FinOps_Analysis.md` · `Failure_Log_Phase2.md` · `Demo_Video_Storyboard.md`
- `Phase2_Notebook_Template.md` + `PriceIQ_Phase2_Final.ipynb`

**Phase 3 presentation**
- `Phase3_Slides.pptx` — 8 张 deck（v0.dev 风，含真 Streamlit screenshot）— 由 build_pptx.py 生成，**不要手改 .pptx**
- `Phase3_Speaker_Notes.md` — 每 slide 30-90s 演讲稿
- `Phase3_QA_Cheatsheet.md` — 18 个高频提问 + ≤20s 答案
- `build_pptx.py` / `audit_pptx.py` / `capture_demo.py` — PPT 生成 + audit + 截图工具
- `assets/demo_*.png` — Streamlit 截图

**Other**
- `requirements.txt` · `.streamlit/config.toml` · `.gitignore`
- `DEPLOY.md` — Streamlit Cloud / HF Spaces / cloudflared tunnel 部署指南
- `README.md` — 入口

---

## PPT / 视觉产物的强制工作流（修排版默认开）

任何修改 `build_pptx.py` 或 `Phase3_Slides.pptx` 的任务，**完成后必须自动跑 audit + 修复**，不要等用户主动催：

1. **改完立即跑 audit**：
   ```bash
   python3 build_pptx.py && python3 audit_pptx.py Phase3_Slides.pptx
   ```
   `audit_pptx.py` 检查每张 slide：shape 越界 / 字号 < 10pt / 字号分布 / 字符密度。

2. **issues > 0 必须当场修**。常见原因：
   - Emu / 2 这类除法 → 用 `_i()` helper 强转 int
   - footer rule 6.95" 之下不能放 footnote / textbox
   - body textbox height 给太大 → audit 报 bottom 越底
   - 升字号后未同步加 textbox height → 文字被覆盖

3. **PowerPoint reload 强制**：build_pptx.py 重写 `.pptx` 后，PowerPoint **不会自动 reload**。必须用 AppleScript：
   ```bash
   osascript -e 'tell application "Microsoft PowerPoint"
     close active presentation saving no
     delay 0.5
     open POSIX file "/path/to/Phase3_Slides.pptx"
   end tell'
   ```

4. **设计 token（不可破坏）**：
   - 单 accent：red `#DC2626`；其它颜色仅用语义（positive=green, warn=yellow, info=blue, violet=violet）
   - 字体：`Inter` body / `JetBrains Mono` code / 字重 400–600（不要 700+）
   - 字号阶：display 80–120pt / h1 28–44pt / body 16–22pt / caption 12–14pt / eyebrow 11pt
   - 圆角：6px chip / 8px card / 10px box
   - footer rule 6.95"，footer text 7.05"，footnote ≤ 6.45"

5. **每次改完报告必须包含**：(a) audit issues 多少；(b) 每张 slide 检查清单是否过；(c) 哪些 token 动过

---

## Colab .ipynb 同步规则

任何 `priceiq_*.py` 改动后，`PriceIQ_Phase2_Final.ipynb` 里嵌入的副本会过期（grader 在 Colab 跑的不是 disk module 而是 ipynb cell 里的 `%%writefile`）。所以：

```bash
python3 build_ipynb.py    # rebuild from current priceiq_*.py
```

提交前确保 .ipynb 已 sync。

---

## Streamlit demo 部署选项

`streamlit run app.py` 本地 / Streamlit Community Cloud 永久 / Cloudflare
quick tunnel 临时 — 完整步骤见 `DEPLOY.md`。

---

## Claude Code CLI 使用

在项目目录跑 `claude`，这份 CLAUDE.md 自动加载。直接说要做什么，不要重述背景。
