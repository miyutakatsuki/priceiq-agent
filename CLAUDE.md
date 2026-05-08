# CLAUDE.md — PriceIQ Agent Project

> 用途：跨环境迁移上下文（Cowork → Claude Code CLI）。新会话开始时直接读这份文件。
> 当前阶段：**Phase 1 已完成，准备进入 Phase 2**

---

## 用户偏好（必须遵守）

- **语言**：默认中文回复，专业术语保留英文原文
- **作业答案生成时**：用英文
- **回复原则**：结论前置、不说废话、不确定就说不确定、欢迎被反驳
- **格式**：短问题→简短回答无列表；复杂问题→结构化；代码→完整可运行+简短注释

---

## PPT / 视觉产物的强制工作流（修排版默认开）

任何修改 `build_pptx.py` 或 `Phase3_Slides.pptx` 的任务，**完成后必须自动执行 audit + 修复**，不要等用户主动催：

1. **改完立即跑 audit**：
   ```bash
   python3 build_pptx.py && python3 audit_pptx.py Phase3_Slides.pptx
   ```
   `audit_pptx.py` 检查每张 slide 的：
   - shape 是否越出 13.33"×7.5" 画布
   - 文字字号 < 10pt（warn）/ < 8pt（critical）
   - 字号分布 + 字符数（用来判断信息密度）

2. **issues > 0 必须当场修**，不能交付。常见原因：
   - 用 Emu / 2 这类除法 → 用 `_i()` helper 强转 int
   - footer rule 6.95" 之下不能放 footnote / textbox
   - body textbox height 给太大 → audit 报 bottom 越底（视觉 OK 但定义不对）
   - 升字号后未同步加 textbox height → 文字被 footnote / 下一块覆盖

3. **视觉验证（PowerPoint reload 强制）**：build_pptx.py 重写 `Phase3_Slides.pptx` 后，PowerPoint **不会自动 reload**。必须用 AppleScript 强制重开：
   ```bash
   osascript -e 'tell application "Microsoft PowerPoint"
     close active presentation saving no
     delay 0.5
     open POSIX file "/path/to/Phase3_Slides.pptx"
   end tell'
   ```
   否则用户看到的还是旧版本，会以为修改没生效。

4. **设计 token（不可破坏）**：
   - 单 accent：red `#DC2626`；其它颜色仅用于语义（positive=green, warn=yellow, info=blue, violet=violet）
   - 字体：`Inter` body / `JetBrains Mono` code / 字重 400-600（不要 700+）
   - 字号阶：display 80-120pt / h1 28-44pt / body 16-22pt / caption 12-14pt / eyebrow 11pt
   - 圆角：6px chip / 8px card / 10px box
   - footer rule 固定在 6.95"，footer text 7.05"，footnote ≤ 6.45"

5. **每次改完报告必须包含**：(a) 跑了 audit、issues 多少；(b) 每张 slide 检查清单是否过；(c) 哪些 token 有动过

附属文件：
- `build_pptx.py` — 生成器（编辑这个，不要直接改 .pptx）
- `audit_pptx.py` — 排版 audit
- `capture_demo.py` — Streamlit demo 截图（playwright + chromium）
- `assets/demo_*.png` — 截图素材

---

## 项目一句话

输入自然语言定价问题 → Planner + Executor 双 agent → 调 4 个工具 → 输出基于 Olist 真实数据的价格弹性 + 收益模拟建议

---

## 课程信息

- **课程**：Generative AI（JHU Carey 商学院）
- **团队**：Kangchun Sun · Tao Cheng · Maoyuan Li（3人）
- **Track B**：Claude Agent SDK，手写 tool_use loop，Planner + Executor 架构
- **不用** Managed Agents（老师要 manual orchestration）

## 评分结构

| 阶段 | 截止 | 占分 | 状态 |
|------|------|------|------|
| Phase 1：提案 + prototype | Week 5 (M5) | 30% | ✅ 已完成 |
| Phase 2：最终代码 + 报告 + demo 视频 | Week 8 | 50% | 进行中 |
| Phase 3：现场 5 分钟 presentation + Q&A | Week 8 | 20% | 待办 |

---

## Phase 1 状态：已完成 ✅

所有文件在 `C:\Users\25041\Desktop\genai-final project\`：

| 文件 | 说明 | 状态 |
|------|------|------|
| `PriceIQ_Phase1_Proposal.pdf` | 4页提案，6个section | ✅ 已提交 |
| `PriceIQ_Phase1_Prototype.ipynb` | Colab notebook，28个cell，可运行 | ✅ 已提交 |
| `PriceIQ_Failure_Log.docx` | 测试失败记录表（上传到 Google Drive 用） | ✅ 已创建 |
| `Project_Brief.md` | 团队简报 | ✅ 已更新 |

**提交方式**：Assignment 3（以作业3名义提交）

---

## 技术架构

```
User Query (NL)
      ↓
Planner Agent (claude-sonnet-4-5)
  - XML few-shot prompt: <context> <task> <examples> <rules>
  - 解析意图，映射 Olist 品类，决定调哪些工具
      ↓
Executor Agent (claude-haiku-4-5)
  - 手写 tool_use loop（Track B，无 Managed Agents）
  - MAX_ITERATIONS=8 kill switch
  - 超 8K 字符自动压缩 memory
      ↓
4 Tools → Structured Output
```

## 4 个工具

| 工具 | 数据源 | 核心计算 |
|------|--------|---------|
| `query_sales_data(category, start_date, end_date)` | Olist SQLite | SQL 查询，返回价格-销量分布 |
| `calculate_price_elasticity(category)` | Tool 1 输出 | scipy OLS: ln(Q)=α+β·ln(P)，返回 β、R²、95% CI |
| `get_demand_signals(category, country='BR')` | pytrends + 节假日 CSV | Google Trends 指数 + 距下个节假日天数；pytrends 失败→季节性降级 |
| `simulate_revenue_impact(category, price_change_pct)` | Tools 2+3 | adj_β=β×demand_mult; new_qty=current_qty×(1+Δp)^adj_β；输出3场景 |

## 数据来源

- **Olist Brazilian E-Commerce**（Kaggle 免费，SQLite，10万真实订单，2016-2018，73个品类）
  - CSV: https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce
  - SQLite: https://www.kaggle.com/datasets/terencicp/e-commerce-dataset-by-olist-as-an-sqlite-database
- **pytrends**：Google Trends Python 库，无需 API key
- **巴西节假日 CSV**：静态文件，已内置在 notebook
- **OpenWeather API**：免费层，仅天气敏感品类（运动、园艺）条件调用

---

## 安全机制（已实现）

- Kill switch：`MAX_ITERATIONS = 8`
- Memory 压缩：历史超 8K 字符时自动 summarize，注入 `<memory_summary>`
- Graceful degradation：pytrends 失败 → 季节性估算兜底
- API key：仅通过 Colab Secrets 读取，代码里不出现明文

---

## No-Go Zone（自动扣分）

- **-10 分**：用 Claude.ai 网页 UI 做 demo
- **-10 分**：Hard-code 测试答案
- **-5 分**：API key 出现在代码或报告里

---

## Phase 2 待办（Week 8 截止）

1. **加载真实 Olist SQLite**（替换 notebook 里的合成数据）
2. **扩展到全部 73 个 Olist 品类**
3. **接入 OpenWeather API**（运动/园艺品类天气信号）
4. **完成 10 个 gold standard 测试用例**（提案里有 5 个，再补 5 个）
5. **持续更新 Failure Log**（每次测试后粘贴代码+输出到 Google Doc）
6. **最终报告**（5-7 页，含 red-teaming 章节）
7. **5 分钟 demo 视频**（YouTube 录制，展示 agent 真实运行过程）

---

## 老师硬性门槛（已满足，Phase 2 继续保持）

| 要求 | 实现 | 状态 |
|------|------|------|
| 多步推理 ≥3 步 | 4 个工具串行调用 + THOUGHT 内部独白 | ✅ |
| 分析性转换 | scipy OLS 回归 + 收益数学公式 | ✅ |
| 模糊意图处理 | Planner 解析自然语言，映射葡语品类名 | ✅ |
| Few-shot + XML tagging | `<context>` `<task>` `<examples>` `<rules>` | ✅ |
| Memory 手动管理 | 8K 字符触发压缩，注入 memory_summary | ✅ |
| Graceful degradation | pytrends 降级，SQL 数据不足时扩展日期范围 | ✅ |
| Failure log | `PriceIQ_Failure_Log.docx`，上传 Google Drive | ✅ |
| Out-of-scope 声明 | 提案和代码里均已标注 | ✅ |

---

## Claude Code CLI 使用说明

在项目目录下运行 `claude` 即可，这份 CLAUDE.md 会自动被读取。

直接说你要做什么，不需要重新解释项目背景。
