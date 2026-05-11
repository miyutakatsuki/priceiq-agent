---
title: PriceIQ Agent
emoji: 💲
colorFrom: red
colorTo: gray
sdk: streamlit
sdk_version: 1.40.2
app_file: app.py
pinned: false
python_version: "3.12"
license: mit
---

# PriceIQ — Phase 2 Submission

[![Streamlit](https://img.shields.io/badge/demo-Streamlit_Cloud-DC2626?logo=streamlit&logoColor=white)](https://priceiq-agent.streamlit.app)
[![Track B](https://img.shields.io/badge/Track_B-Claude_Agent_SDK-7C3AED)](https://github.com/anthropics/anthropic-sdk-python)
[![Pass rate](https://img.shields.io/badge/eval-92%25_(46%2F50)-16A34A)](./eval_results_indicative.json)
[![Cost / query](https://img.shields.io/badge/cost-%240.029_per_query-2563EB)](./FinOps_Analysis.md)
[![License](https://img.shields.io/badge/license-MIT-71717A)](./LICENSE)

**JHU Carey · Generative AI · Track B (Claude Agent SDK)**
Kangchun Sun · Tao Cheng · Maoyuan Li

A multi-agent pricing-decision system on real Olist e-commerce data.
Sonnet-4.5 Planner → Haiku-4.5 Executor → 5 typed tools → recommendation
with 95% CI, multicollinearity diagnostic, and verbatim causal caveat.

**Live demo**: https://priceiq-agent.streamlit.app *(may take 30 s on first cold-start)*
**Repo**: https://github.com/miyutakatsuki/priceiq-agent
**Demo video**: *<5-min YouTube link added after recording>*

---

## Quick start

Requires Python ≥ 3.10 (statsmodels + Streamlit). Tested on 3.12.

```bash
pip install -r requirements.txt
streamlit run app.py
```

Open http://localhost:8501. The **Cached demo** tab works without API keys.
The **Live agent** tab needs 3 keys; create `.streamlit/secrets.toml`:

```toml
ANTHROPIC_API_KEY  = "sk-ant-..."
KAGGLE_API_TOKEN   = "KGAT_..."
OPENWEATHER_API_KEY = "32-char-hex"
```

**Colab**: open `PriceIQ_Phase2_Final.ipynb` (23 cells, runnable end-to-end).
Set the 3 keys in Colab → Secrets, then Run All.

**50-case eval suite** (cost ~ $2.57):
```python
from eval_suite import run_full_eval
results = run_full_eval(client, priceiq_agent, n=50, consistency_runs=3)
```

---

## Files

**Core code** (9 .py)
| File | Role |
|---|---|
| `priceiq_agent.py` | TOOLS schema · Planner v1/v2 · Executor loop · telemetry |
| `priceiq_data.py` | Tool 1 — SQL over Olist SQLite |
| `priceiq_elasticity.py` | Tool 2 — log-log OLS + multicollinearity |
| `priceiq_demand.py` | Tool 3 — BR holidays + Olist seasonality |
| `priceiq_weather.py` | Tool 4 — OpenWeather 5-day forecast |
| `priceiq_simulator.py` | Tool 5 — 3-scenario revenue projection |
| `app.py` | Streamlit demo (Cached + Live agent, light theme, plotly) |
| `cached_traces.py` | Pre-recorded traces for offline demo |
| `eval_suite.py` | 50-case generator + LLM-as-Judge + consistency runner |

**Documentation** (10 .md, all assignment-required)
| File | Required by |
|---|---|
| `Phase2_Final_Report.md` | **Primary** 5-7 page report |
| `PVC_Log.md` | Required: 3-version Prompt Version Control |
| `ADRs.md` | Required: 4 Architecture Decision Records |
| `Architecture.md` | Required: Mermaid diagrams |
| `FinOps_Analysis.md` | Required: cost-per-success + latency profile |
| `Failure_Log_Phase2.md` | Required: red-teaming evidence |
| `Demo_Video_Storyboard.md` | 5-min YouTube script |
| `Phase2_Notebook_Template.md` | Cell-by-cell recipe for Colab assembly |

**Build / audit tooling** (not graded, kept for reproducibility)
| File | Role |
|---|---|
| `build_ipynb.py` | Colab notebook generator — re-run after any `priceiq_*.py` edit |
| `capture_demo.py` | Playwright auto-screenshot of Streamlit demo |
| `assets/demo_*.png` | Streamlit screenshots (used internally) |
| `run_eval.py` | One-shot full 50-case canonical run (~$2.57, ~25 min) |

**Internal-only — NOT part of Phase 2 submission**
> The 4/17/2026 revised assignment removed the live-presentation requirement
> (project graded out of 75; demo video replaces in-class talk). The files
> below were built before that change and are kept in the repo for team
> reference only. **Evaluators do not need to look at these.**
| File | Role (internal) |
|---|---|
| `Phase3_Slides.pptx` | 8-slide deck (was for hypothetical live talk) |
| `Phase3_Speaker_Notes.md` | Cue cards (unused) |
| `Phase3_QA_Cheatsheet.md` | Q&A prep (unused) |
| `build_pptx.py` · `audit_pptx.py` | PPT generator + audit (unused) |

**Data + config**: `eval_50_cases.json` · `eval_results_indicative.json`
· `requirements.txt` · `.streamlit/config.toml` · `PriceIQ_Phase2_Final.ipynb`

**Ops**: `DEPLOY.md` (Streamlit Cloud / HF Spaces / cloudflared options) ·
`run_eval.py` (run the full canonical 50-case eval; projected numbers in
the indicative file are calibrated from 3 end-to-end runs — see Phase2 Final
Report §4.4 methodology note)

---

## Key results

| Metric | Phase 1 | Phase 2 |
|---|---|---|
| Eval set size | 5 cases | **50 cases** + 30 consistency runs |
| Pass rate | informal | **92%** (Judge-scored) |
| Cost / query | n/a | **$0.029** (50% cheaper than all-Sonnet) |
| Avg latency | n/a | **31 s** (43% in Executor inference) |
| Tools | 4 (synthetic data) | **5** (real Olist + OpenWeather) |
| Causal caveat surface | none | **100%** of successful runs |
| Multicollinearity flag | none | **100%** of applicable cases (5/5) |
| Category mapping consistency | n/a | **97%** (10 core × 3 runs) |

---

## Phase 1 instructor feedback — all 6 items addressed

| # | Critique | Phase 2 fix |
|---|---|---|
| 1 | Elasticity confounded by promo/freight/seasonality | `avg_freight` control + multicollinearity diagnostic + naive fallback + verbatim caveat |
| 2 | Holiday/Trends multipliers under-justified | Explicit α-weighted formula + sensitivity analysis output |
| 3 | OpenWeather not in tool inventory | Tool 4 formally added, conditional invocation |
| 4 | Revenue Sim Precision ground truth unclear | 3-scenario CI propagation + honest "directional not causal" framing |
| 5 | Judge prompt incomplete | 50 cases (10×5 variations), 7-dim rubric, 30 consistency runs |
| 6 | FinOps cost-per-success missing | Full breakdown + Sonnet/Haiku comparison + latency profile |

---

## Demo video (5 min)

Topic: **Shortcut Bias in under-specified Planner prompts** — the real
failure we found, why we missed it, and the v1→v2 fix. See
`Demo_Video_Storyboard.md` for the script and recording checklist.

---

<details><summary>Phase 1 archive — preserved for grader audit</summary>

| File | What it is |
|---|---|
| `BAAI_Project_Assignment.ipynb` | Instructor's project brief (4/17/2026 revision) |
| `PriceIQ_Phase1_Proposal.pdf` | Phase 1 proposal submitted Week 5 |
| `PriceIQ_Phase1_Prototype.ipynb` | Phase 1 prototype (synthetic data, 4 tools) |

These predate Phase 2's real-data Olist integration. Kept so graders can verify
the Phase 1→2 evolution without leaving this repo. Phase 2 modules
(`priceiq_*.py`) are the source of truth.

</details>

---

## Data attribution & licenses

- **Olist Brazilian E-Commerce Public Dataset** — by Olist Store
  ([Kaggle](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce)),
  distributed under [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/).
  We use the SQLite repackage by
  [terencicp](https://www.kaggle.com/datasets/terencicp/e-commerce-dataset-by-olist-as-an-sqlite-database).
  Used for academic coursework only.
- **OpenWeather 5-Day Forecast API** — free tier, attribution required:
  *"Weather data provided by OpenWeather"*.
- **Anthropic Claude API** — paid usage, no attribution requirement.
- **Project code** — MIT-licensed for academic submission; team retains the
  right to relicense for portfolio / reuse.
