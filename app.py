"""PriceIQ Streamlit demo — customer-facing pricing decision agent.

Run:    streamlit run app.py
Open:   http://localhost:8501

Tabs:
  Cached demo · Live agent
  (Evaluator artifacts — PVC log, FinOps, architecture — live in repo .md
  files; the demo UI is the customer view, not the grading dashboard.)

Visual:
  Linear/Vercel-inspired minimal flat design — neutral palette + single
  accent (#FF6B6B), Inter font, design-token CSS variables.

Data sources:
  Cached demo: zero API keys (uses cached_traces).
  Live agent: requires ANTHROPIC_API_KEY + KAGGLE_API_TOKEN +
              OPENWEATHER_API_KEY in .streamlit/secrets.toml or env vars.

Helpers:
  section_header / pill / render_trace_steps / render_recommendation_cards
  render_causal_caveat / plot_revenue_scenarios
"""

# ── Skip Streamlit first-run email prompt (deploy-host-only) ──
# Streamlit Cloud / Hugging Face / Render containers don't pre-populate
# ~/.streamlit/credentials.toml, so the first launch prompts for an email
# and stalls the healthz check. Write an empty credentials file before
# anything imports streamlit so the prompt never fires.
import os as _os
_cred_dir = _os.path.expanduser("~/.streamlit")
_cred_path = _os.path.join(_cred_dir, "credentials.toml")
if not _os.path.exists(_cred_path):
    _os.makedirs(_cred_dir, exist_ok=True)
    with open(_cred_path, "w") as _f:
        _f.write('[general]\nemail = ""\n')

import json
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import numpy as np
import pandas as pd

from cached_traces import GARDEN_TRACE, SPORTS_TRACE, SPORTS_V1_TRACE, CATEGORIES, PROMPTS


# ── Page config ──────────────────────────────────────────────
st.set_page_config(
    page_title="PriceIQ — Pricing Decision Agent",
    page_icon="💲",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS — minimal, design-token driven, Linear/Vercel-inspired ──
st.markdown("""
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">

<style>
    /* ── Design tokens — v0.dev / Vercel light theme ─────── */
    :root {
        /* zinc neutral palette (light) */
        --bg-base:       #FAFAFA;       /* zinc-50  page bg  */
        --bg-raised:     #FFFFFF;       /* white    cards    */
        --bg-overlay:    #F4F4F5;       /* zinc-100 hover    */
        --bg-muted:      #F9FAFB;       /* gray-50  subtle   */
        --border:        #E4E4E7;       /* zinc-200 hairline */
        --border-strong: #D4D4D8;       /* zinc-300          */
        --fg-primary:    #09090B;       /* zinc-950 body     */
        --fg-secondary:  #52525B;       /* zinc-600 caption  */
        --fg-tertiary:   #A1A1AA;       /* zinc-400 muted    */
        /* multi-accent palette (v0-style) */
        --accent:        #DC2626;       /* red-600  brand    */
        --accent-soft:   #FEE2E2;       /* red-100  bg fill  */
        --positive:      #16A34A;       /* green-600         */
        --positive-soft: #DCFCE7;       /* green-100         */
        --warning:       #CA8A04;       /* yellow-600        */
        --warning-soft:  #FEF9C3;       /* yellow-100        */
        --info:          #2563EB;       /* blue-600          */
        --info-soft:     #DBEAFE;       /* blue-100          */
        --violet:        #7C3AED;       /* violet-600        */
        --violet-soft:   #EDE9FE;       /* violet-100        */
    }

    .stApp { background: var(--bg-raised); }

    /* ── Typography ───────────────────────────────────────── */
    html, body, [class*="css"] {
        font-family: 'Inter', system-ui, -apple-system, sans-serif !important;
        font-feature-settings: 'cv02','cv03','cv04','cv11','tnum','ss01';
        letter-spacing: -0.011em;
        color: var(--fg-primary);
    }
    code, pre, .stCodeBlock { font-family: 'JetBrains Mono','SF Mono',monospace !important; }
    h1, h2, h3, h4 { letter-spacing: -0.022em; font-weight: 600; color: var(--fg-primary); }
    h1 { font-size: 2rem !important; }
    h2 { font-size: 1.4rem !important; padding-top: 0.4rem; }
    h3 { font-size: 1.1rem !important; }
    p, li { color: var(--fg-secondary); }

    /* ── Hero: light card, multi-accent gradient stripe ──── */
    .hero {
        position: relative;
        padding: 1.1rem 1.5rem 1.2rem 1.5rem;
        border-radius: 10px;
        margin-bottom: 0.85rem;
        background: var(--bg-raised);
        border: 1px solid var(--border);
        overflow: hidden;
    }
    .hero::before {
        content: ""; position: absolute;
        top: 0; left: 0; right: 0; height: 2px;
        background: linear-gradient(90deg,
            var(--accent) 0%, var(--warning) 33%,
            var(--positive) 66%, var(--info) 100%);
    }
    .hero h1 {
        color: var(--fg-primary); margin: 0;
        font-size: 1.5rem !important; font-weight: 600;
        letter-spacing: -0.025em;
    }
    .hero .subtitle {
        color: var(--fg-secondary); margin-top: 0.3rem;
        font-size: 0.88rem; font-weight: 400; max-width: 640px; line-height: 1.5;
    }
    .hero .badges { margin-top: 0.7rem; display: flex; gap: 0.4rem; flex-wrap: wrap; }
    .hero .badge {
        display: inline-flex; align-items: center; gap: 0.35rem;
        background: var(--bg-muted);
        border: 1px solid var(--border);
        color: var(--fg-secondary);
        padding: 0.25rem 0.65rem;
        border-radius: 6px;
        font-size: 0.74rem; font-weight: 500;
        font-feature-settings: 'tnum';
    }
    .hero .badge .dot {
        width: 6px; height: 6px; border-radius: 50%;
        background: var(--positive);
    }
    .hero .badge.accent { color: var(--accent); border-color: var(--accent-soft); background: var(--accent-soft); }

    /* ── Streamlit metric ─────────────────────────────────── */
    [data-testid="stMetric"] {
        background: var(--bg-raised);
        padding: 0.85rem 1rem;
        border-radius: 8px;
        border: 1px solid var(--border);
        transition: border-color 0.15s ease;
    }
    [data-testid="stMetric"]:hover { border-color: var(--border-strong); }
    [data-testid="stMetricLabel"] {
        color: var(--fg-secondary) !important; font-size: 0.72rem !important;
        text-transform: uppercase; letter-spacing: 0.06em; font-weight: 500;
    }
    [data-testid="stMetricValue"] {
        color: var(--fg-primary) !important; font-weight: 600 !important;
        font-size: 1.5rem !important; font-feature-settings: 'tnum';
        letter-spacing: -0.02em;
    }
    [data-testid="stMetricDelta"] { font-size: 0.76rem !important; font-weight: 500 !important; }

    /* ── Caveat banner — yellow tint ──────────────────────── */
    .caveat-banner {
        background: var(--warning-soft);
        border: 1px solid #FDE68A;
        border-radius: 8px;
        padding: 0.7rem 0.95rem;
        margin: 0.65rem 0;
        color: #713F12;
        font-size: 0.83rem; line-height: 1.5;
    }
    .caveat-banner strong { color: #854D0E; font-weight: 600; }

    /* ── Section header — small caps ──────────────────────── */
    .section-h {
        display: flex; align-items: center; gap: 0.5rem;
        font-size: 0.74rem; font-weight: 600;
        color: var(--fg-secondary);
        text-transform: uppercase; letter-spacing: 0.08em;
        margin: 1.5rem 0 0.65rem 0;
    }

    /* ── Pills ────────────────────────────────────────────── */
    .pill {
        display: inline-flex; align-items: center; gap: 0.3rem;
        padding: 0.15rem 0.55rem; border-radius: 6px;
        font-size: 0.7rem; font-weight: 500;
        font-feature-settings: 'tnum';
    }
    .pill.success { background: var(--positive-soft); color: var(--positive); border: 1px solid #BBF7D0; }
    .pill.warn    { background: var(--warning-soft);  color: var(--warning);  border: 1px solid #FDE68A; }
    .pill.info    { background: var(--info-soft);     color: var(--info);     border: 1px solid #BFDBFE; }
    .pill.danger  { background: var(--accent-soft);   color: var(--accent);   border: 1px solid #FECACA; }

    /* ── Tabs ─────────────────────────────────────────────── */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0;
        background: transparent;
        padding: 0;
        border-bottom: 1px solid var(--border);
        margin-bottom: 1rem;
    }
    .stTabs [data-baseweb="tab"] {
        height: 38px;
        padding: 0 16px;
        background: transparent !important;
        border-radius: 0;
        color: var(--fg-secondary) !important;
        font-weight: 500; font-size: 0.86rem;
        border-bottom: 2px solid transparent;
        transition: color 0.15s ease, border-color 0.15s ease;
    }
    .stTabs [data-baseweb="tab"]:hover { color: var(--fg-primary) !important; }
    .stTabs [aria-selected="true"] {
        color: var(--fg-primary) !important;
        border-bottom-color: var(--fg-primary) !important;
        background: transparent !important;
        box-shadow: none !important;
        font-weight: 600;
    }

    /* ── Code blocks ──────────────────────────────────────── */
    .stCodeBlock, [data-testid="stCodeBlock"] {
        background: var(--bg-overlay) !important;
        border: 1px solid var(--border) !important;
        border-radius: 8px !important;
        color: var(--fg-primary) !important;
    }
    .stCodeBlock code { color: var(--fg-primary) !important; }

    /* ── Sidebar — recessed zinc-50, narrower (240px) ────── */
    [data-testid="stSidebar"] {
        background: var(--bg-base) !important;
        border-right: 1px solid var(--border);
        min-width: 240px !important;
        max-width: 260px !important;
        width: 240px !important;
    }
    [data-testid="stSidebar"] > div { background: var(--bg-base) !important; }
    [data-testid="stSidebar"] .stRadio > div { gap: 0.3rem; }
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] { color: var(--fg-secondary); }

    /* ── Radio buttons (sample picker) ────────────────────── */
    .stRadio [role="radiogroup"] label {
        background: var(--bg-raised);
        border: 1px solid var(--border);
        padding: 0.35rem 0.75rem;
        border-radius: 6px;
        font-size: 0.82rem;
        margin: 0 4px 0 0;
        transition: all 0.15s ease;
    }
    .stRadio [role="radiogroup"] label:hover { border-color: var(--border-strong); }

    /* ── Dataframe ────────────────────────────────────────── */
    [data-testid="stDataFrame"] {
        border-radius: 8px; overflow: hidden;
        border: 1px solid var(--border);
    }

    /* ── Primary button ───────────────────────────────────── */
    .stButton > button {
        background: var(--fg-primary) !important;
        color: var(--bg-raised) !important;
        border: 1px solid var(--fg-primary) !important;
        border-radius: 6px !important;
        font-weight: 500 !important;
        font-size: 0.86rem !important;
        padding: 0.45rem 1rem !important;
        transition: opacity 0.15s ease;
    }
    .stButton > button:hover { opacity: 0.88; }

    /* ── Footer ───────────────────────────────────────────── */
    .footer {
        margin-top: 3rem; padding-top: 1.25rem;
        border-top: 1px solid var(--border);
        color: var(--fg-tertiary); font-size: 0.78rem;
        display: flex; justify-content: space-between; flex-wrap: wrap; gap: 1rem;
    }
    .footer a { color: var(--fg-secondary); text-decoration: none; }
    .footer a:hover { color: var(--accent); }

    /* ── Tables in markdown ───────────────────────────────── */
    [data-testid="stMarkdownContainer"] table {
        margin: 0.5rem 0; font-size: 0.85rem;
        border-radius: 8px; overflow: hidden;
        border: 1px solid var(--border);
    }
    [data-testid="stMarkdownContainer"] table th {
        background: var(--bg-overlay); color: var(--fg-secondary);
        font-weight: 500; font-size: 0.72rem;
        text-transform: uppercase; letter-spacing: 0.05em;
        border-bottom: 1px solid var(--border);
    }
    [data-testid="stMarkdownContainer"] table td { color: var(--fg-primary); }
    [data-testid="stMarkdownContainer"] blockquote {
        border-left: 3px solid var(--accent);
        background: var(--accent-soft);
        padding: 0.55rem 0.85rem; border-radius: 0 6px 6px 0;
        margin: 0.6rem 0; font-size: 0.86rem; color: #7F1D1D;
    }

    /* ── Expanders ────────────────────────────────────────── */
    [data-testid="stExpander"] {
        background: var(--bg-raised);
        border: 1px solid var(--border) !important;
        border-radius: 8px !important;
    }
    [data-testid="stExpander"] summary { color: var(--fg-secondary) !important; }

    /* ── Recommendation card grid (4 cols, force 4 abreast) ── */
    .rec-grid {
        display: grid;
        grid-template-columns: repeat(4, minmax(0, 1fr));
        gap: 0.6rem;
        margin: 0.4rem 0;
    }
    @media (max-width: 1024px) {
        .rec-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
    }
    .rec-card {
        background: var(--bg-raised);
        border: 1px solid var(--border);
        border-radius: 10px;
        padding: 0.95rem 1.05rem;
        position: relative;
        transition: border-color 0.15s ease;
    }
    .rec-card:hover { border-color: var(--border-strong); }
    .rec-card .label {
        font-size: 0.68rem; font-weight: 500; color: var(--fg-secondary);
        text-transform: uppercase; letter-spacing: 0.08em;
        margin-bottom: 0.35rem;
        display: flex; align-items: center; justify-content: space-between;
    }
    .rec-card .label .marker {
        width: 6px; height: 6px; border-radius: 50%;
        background: var(--fg-tertiary);
    }
    .rec-card .value {
        font-size: 1.4rem; font-weight: 600; color: var(--fg-primary);
        font-feature-settings: 'tnum'; letter-spacing: -0.02em;
        line-height: 1.15;
    }
    .rec-card .meta {
        margin-top: 0.3rem; font-size: 0.74rem; color: var(--fg-secondary);
        line-height: 1.45;
    }
    .rec-card.accent .label .marker { background: var(--accent); }
    .rec-card.accent .value { color: var(--accent); }
    .rec-card.ok     .label .marker { background: var(--positive); }
    .rec-card.ok     .value { color: var(--positive); }
    .rec-card.warn   .label .marker { background: var(--warning); }
    .rec-card.warn   .value { color: var(--warning); }
    .rec-card.info   .label .marker { background: var(--info); }
    .rec-card.info   .value { color: var(--info); }

    /* ── Horizontal trace timeline ────────────────────────── */
    .timeline {
        position: relative;
        display: grid; grid-auto-flow: column; grid-auto-columns: 1fr;
        align-items: start;
        margin: 0.5rem 0;
        padding: 0.4rem 0;
    }
    .timeline::before {
        content: ""; position: absolute;
        left: 8%; right: 8%; top: 1.5rem;
        height: 1px; background: var(--border);
    }
    .timeline .node {
        position: relative; text-align: center;
        padding: 0 0.25rem;
    }
    .timeline .node .dot {
        width: 28px; height: 28px;
        margin: 0 auto 0.45rem auto;
        border-radius: 50%;
        background: var(--bg-raised);
        border: 1px solid var(--border-strong);
        display: flex; align-items: center; justify-content: center;
        font-size: 0.76rem; font-weight: 600; color: var(--fg-secondary);
        position: relative; z-index: 1;
        transition: all 0.18s ease;
    }
    .timeline .node:hover .dot {
        background: var(--info-soft);
        border-color: var(--info);
        color: var(--info);
    }
    .timeline .node .dot.ok    { background: var(--positive-soft); border-color: var(--positive); color: var(--positive); }
    .timeline .node .dot.error { background: var(--accent-soft);   border-color: var(--accent);   color: var(--accent); }
    .timeline .node .name {
        font-size: 0.72rem; font-weight: 500; color: var(--fg-primary);
        line-height: 1.25;
    }
    .timeline .node .meta {
        font-size: 0.66rem; color: var(--fg-tertiary);
        font-family: 'JetBrains Mono', monospace;
        margin-top: 0.15rem;
    }

    /* ── st.info / st.warning / st.success / st.error tone ── */
    [data-testid="stAlert"] {
        border-radius: 8px !important;
        border: 1px solid var(--border) !important;
        font-size: 0.86rem !important;
    }

    /* Hide streamlit chrome (Deploy button, top toolbar, branding) */
    #MainMenu, footer { visibility: hidden; }
    [data-testid="stHeader"] { background: transparent; height: 0; }
    [data-testid="stToolbar"] { display: none; }
    [data-testid="stDeployButton"] { display: none; }
    .stApp [data-testid="stStatusWidget"] { display: none; }

    /* Wider main content area */
    .main .block-container,
    [data-testid="stMain"] .block-container {
        max-width: 1280px !important;
        padding-top: 1rem !important;
        padding-left: 2rem !important;
        padding-right: 2rem !important;
    }
</style>
""", unsafe_allow_html=True)


# ── Plotly theme — light, v0/Tailwind palette ────────────────
PLOTLY_TEMPLATE = "plotly_white"
PLOT_COLORS = {
    "primary":   "#DC2626",   # red-600   — same as --accent
    "secondary": "#2563EB",   # blue-600  — same as --info
    "success":   "#16A34A",   # green-600
    "warn":      "#CA8A04",   # yellow-600
    "danger":    "#DC2626",
    "neutral":   "#A1A1AA",   # zinc-400
    "purple":    "#7C3AED",   # violet-600
    "amber":     "#D97706",   # amber-600
}


def _layout(fig: go.Figure, title: str = None, height: int = 400) -> go.Figure:
    """Apply consistent plot layout (light theme)."""
    fig.update_layout(
        template=PLOTLY_TEMPLATE,
        title=dict(text=title, font=dict(size=14, color="#09090B", family="Inter")) if title else None,
        font=dict(family="Inter", color="#52525B", size=12),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#FFFFFF",
        height=height,
        margin=dict(l=10, r=10, t=46 if title else 16, b=10),
        hoverlabel=dict(bgcolor="#09090B", bordercolor="#09090B",
                        font=dict(family="Inter", color="#FAFAFA", size=12)),
        xaxis=dict(gridcolor="#F4F4F5", zerolinecolor="#E4E4E7", linecolor="#E4E4E7"),
        yaxis=dict(gridcolor="#F4F4F5", zerolinecolor="#E4E4E7", linecolor="#E4E4E7"),
    )
    return fig


def section_header(icon: str, title: str) -> None:
    """Render a styled section label (uppercase muted). `icon` is kept for
    backwards-compat but rendered only if truthy — minimal style favors text."""
    icon_html = f'<span style="opacity:0.6;">{icon}</span> ' if icon else ""
    st.markdown(
        f'<div class="section-h">{icon_html}{title}</div>',
        unsafe_allow_html=True,
    )


def pill(text: str, kind: str = "info", small: bool = False) -> str:
    """Return inline pill HTML. kind ∈ {success, warn, info, danger}."""
    pad = "0.1rem 0.45rem" if small else "0.2rem 0.7rem"
    size = "0.6rem" if small else "0.72rem"
    return (f'<span class="pill {kind}" style="font-size:{size};padding:{pad};">'
            f'{text}</span>')


# Tool icons for visual plan diff
_TOOL_META = {
    "query_sales_data":           ("🗄", "SQL",      "#FF6B6B"),
    "calculate_price_elasticity": ("📈", "OLS",      "#FFA94D"),
    "get_demand_signals":         ("📅", "Demand",   "#FFD56B"),
    "get_weather_signal":         ("🌦", "Weather",  "#4ECDC4"),
    "simulate_revenue_impact":    ("💵", "Simulate", "#9B7EDC"),
}


def plot_revenue_scenarios(scenarios: dict, current: dict) -> go.Figure:
    """3 场景收益柱状图（light theme）."""
    names = ["Pessimistic", "Central", "Optimistic"]
    keys = ["pessimistic_beta_low", "central", "optimistic_beta_high"]
    revenues = [scenarios[k]["new_revenue_monthly"] for k in keys]
    deltas = [scenarios[k]["revenue_change_pct"] * 100 for k in keys]
    colors = [PLOT_COLORS["warn"], PLOT_COLORS["primary"], PLOT_COLORS["success"]]

    fig = go.Figure()
    baseline = current["monthly_revenue_avg_3mo"]
    fig.add_hline(
        y=baseline, line_dash="dash", line_color="#A1A1AA",
        annotation_text=f"Current ${baseline:,.0f}/mo",
        annotation_position="top left",
        annotation_font=dict(color="#52525B", size=11, family="Inter"),
    )
    fig.add_trace(go.Bar(
        x=names, y=revenues,
        marker=dict(color=colors, line=dict(width=0)),
        text=[f"<b>${r:,.0f}</b><br>{d:+.1f}%" for r, d in zip(revenues, deltas)],
        textposition="outside",
        textfont=dict(size=12, family="Inter", color="#09090B"),
        hovertemplate="<b>%{x}</b><br>Revenue: $%{y:,.0f}<extra></extra>",
        name="Projected revenue",
        width=0.55,
    ))
    _layout(fig, title="Monthly revenue · 3 scenarios from β confidence interval")
    fig.update_layout(
        yaxis_title="Monthly revenue (R$)",
        xaxis_title="",
        showlegend=False,
        bargap=0.4,
    )
    return fig


def render_trace_steps(trace: dict) -> None:
    """Render the tool_use loop as a horizontal timeline (numbered nodes + line)."""
    total_s = sum(tc["latency_s"] for tc in trace["tool_calls"])
    nodes = []
    for tc in trace["tool_calls"]:
        icon, short, _ = _TOOL_META.get(tc["tool"], ("●", tc["tool"][:8], "#71717A"))
        cls = "error" if tc.get("error") else "ok"
        nodes.append(
            f'<div class="node" title="{tc["tool"]} · iter {tc["iter"]} · {tc["latency_s"]}s">'
            f'<div class="dot {cls}">{tc["iter"]}</div>'
            f'<div class="name">{short}</div>'
            f'<div class="meta">{tc["latency_s"]:.1f}s</div>'
            f'</div>'
        )
    st.markdown(
        f'<div style="display:flex;justify-content:space-between;align-items:baseline;'
        f'font-size:0.72rem;color:var(--fg-tertiary);">'
        f'<span style="text-transform:uppercase;letter-spacing:0.08em;font-weight:500;">'
        f'Execution timeline</span>'
        f'<span style="font-family:JetBrains Mono;">'
        f'{len(trace["tool_calls"])} tools · {total_s:.1f}s</span></div>'
        f'<div class="timeline">{"".join(nodes)}</div>',
        unsafe_allow_html=True,
    )


def render_recommendation_cards(trace: dict) -> None:
    """4-card grid: β · best scenario · stability · sample/significance."""
    e = trace["elasticity"]
    s = trace["scenarios"]
    # pick the central scenario as the headline
    central = s["central"]
    rev_pct = central["revenue_change_pct"] * 100
    rev_sign = "+" if rev_pct >= 0 else ""

    # Multicollinearity card
    if e.get("multicollinearity_warning"):
        stab_kind, stab_value, stab_meta = (
            "warn", "Naive fallback",
            f"controlled β = {e['controlled_beta']} · sign-flip detected",
        )
    else:
        stab_kind, stab_value, stab_meta = (
            "ok", "Stable",
            f"controlled β = {e.get('controlled_beta', e['elasticity_beta'])} · no warning",
        )

    sig_kind = "ok" if e["p_value"] < 0.05 else "warn"
    sig_value = "Significant" if e["p_value"] < 0.05 else "Not significant"

    cards = f"""
    <div class="rec-grid">
      <div class="rec-card accent">
        <div class="label">Elasticity β</div>
        <div class="value">{e['elasticity_beta']}</div>
        <div class="meta">{e['elasticity_label'].title()} · 95% CI [{e['ci_95'][0]}, {e['ci_95'][1]}]</div>
      </div>
      <div class="rec-card ok">
        <div class="label">Central revenue change</div>
        <div class="value">{rev_sign}{rev_pct:.1f}%</div>
        <div class="meta">New revenue ${central['new_revenue_monthly']:,.0f} / mo · qty {rev_sign if central['qty_change_pct']>=0 else ''}{central['qty_change_pct']*100:.1f}%</div>
      </div>
      <div class="rec-card {stab_kind}">
        <div class="label">Stability</div>
        <div class="value">{stab_value}</div>
        <div class="meta">{stab_meta}</div>
      </div>
      <div class="rec-card {sig_kind}">
        <div class="label">Significance</div>
        <div class="value">{sig_value}</div>
        <div class="meta">p = {e['p_value']} · n = {e['n_observations']} · R² = {e['r_squared']}</div>
      </div>
    </div>
    """
    st.markdown(cards, unsafe_allow_html=True)


def render_causal_caveat() -> None:
    """Render the standard 'ASSOCIATIONAL ONLY' banner.

    Appended after every successful agent answer so the disclaimer is always
    visually adjacent to the recommendation. Identical text appears in
    `priceiq_elasticity.causal_caveat` (the source of truth).
    """
    st.markdown(
        '<div class="caveat-banner">'
        '<strong>⚠️ ASSOCIATIONAL ONLY — not causal.</strong> '
        "Historical price variation in Olist is confounded by promotions, freight policy, "
        "seasonality, and supply shocks. β reflects price–quantity correlation under chosen controls, "
        "but does NOT prove that lowering price by 10% will causally lift quantity by |β|·10%. "
        "Use as a directional indicator only. A controlled A/B pricing test is required for causal inference."
        "</div>",
        unsafe_allow_html=True,
    )


# ════════════════════════════════════════════════════════════
# SIDEBAR
# ════════════════════════════════════════════════════════════
with st.sidebar:
    # Brand mark — flat monogram, no gradient/shadow
    st.markdown(
        '<div style="display:flex;align-items:center;gap:0.7rem;margin:0.25rem 0 1.25rem 0;">'
        '<div style="width:34px;height:34px;border-radius:8px;'
        'background:var(--accent-soft);border:1px solid rgba(255,107,107,0.3);'
        'display:flex;align-items:center;justify-content:center;">'
        '<span style="font-size:1rem;font-weight:600;color:var(--accent);'
        'letter-spacing:-0.02em;">P</span></div>'
        '<div>'
        '<div style="font-size:1.05rem;font-weight:600;color:var(--fg-primary);'
        'letter-spacing:-0.02em;line-height:1;">PriceIQ</div>'
        '<div style="font-size:0.7rem;color:var(--fg-tertiary);'
        'margin-top:0.15rem;">Pricing decision agent</div>'
        '</div></div>',
        unsafe_allow_html=True,
    )

    section_header("", "Stack")
    st.markdown(
        '<div style="font-size:0.78rem;color:var(--fg-secondary);line-height:1.65;">'
        '<div><b style="color:var(--fg-primary);font-weight:500;">Anthropic SDK</b> '
        '<span style="color:var(--fg-tertiary);">— Sonnet 4.5 + Haiku 4.5</span></div>'
        '<div><b style="color:var(--fg-primary);font-weight:500;">Olist SQLite</b> '
        '<span style="color:var(--fg-tertiary);">— 100K orders</span></div>'
        '<div><b style="color:var(--fg-primary);font-weight:500;">OpenWeather</b> '
        '<span style="color:var(--fg-tertiary);">— 5-day forecast</span></div>'
        '<div><b style="color:var(--fg-primary);font-weight:500;">statsmodels</b> '
        '<span style="color:var(--fg-tertiary);">— OLS + diagnostics</span></div>'
        '<div><b style="color:var(--fg-primary);font-weight:500;">Streamlit · Plotly</b></div>'
        '</div>',
        unsafe_allow_html=True,
    )

    st.markdown("---")
    st.markdown(
        '<div style="font-size:0.72rem;color:var(--fg-tertiary);line-height:1.5;">'
        '<div style="color:var(--fg-secondary);font-weight:500;margin-bottom:0.25rem;'
        'text-transform:uppercase;letter-spacing:0.06em;">Team</div>'
        'Kangchun Sun<br/>Tao Cheng<br/>Maoyuan Li<br/>'
        '<span style="font-size:0.68rem;">JHU Carey · Generative AI · 2026</span>'
        '</div>',
        unsafe_allow_html=True,
    )


# ════════════════════════════════════════════════════════════
# MAIN
# ════════════════════════════════════════════════════════════
st.markdown("""
<div class="hero">
  <h1>PriceIQ</h1>
  <p class="subtitle">
    A pricing decision agent that turns natural-language questions into
    elasticity estimates and 3-scenario revenue projections — grounded in
    100K real Olist orders.
  </p>
  <div class="badges">
    <span class="badge"><span class="dot"></span>Live</span>
    <span class="badge accent">Multi-agent · Claude</span>
    <span class="badge">92% pass · 50-case eval</span>
  </div>
</div>
""", unsafe_allow_html=True)

tab1, tab2 = st.tabs(["Cached demo", "Live agent"])


# ── Tab 1: Cached Demo ───────────────────────────────────────
with tab1:
    # Sample picker — segmented-control style (lives inside Cached demo, not sidebar,
    # so it's only visible when the tab is actually open).
    st.markdown(
        '<div style="display:flex;justify-content:space-between;align-items:baseline;'
        'margin:0.25rem 0 0.5rem 0;">'
        '<div style="font-size:0.72rem;color:var(--fg-tertiary);'
        'text-transform:uppercase;letter-spacing:0.08em;font-weight:500;">'
        'Pre-recorded sample</div>'
        '<div style="font-size:0.72rem;color:var(--fg-tertiary);">'
        'Live runs across all 71 categories &rarr; <b style="color:var(--fg-secondary);">Live agent</b> tab</div>'
        '</div>',
        unsafe_allow_html=True,
    )
    cat_idx = st.radio(
        "Sample picker",
        options=range(len(CATEGORIES)),
        format_func=lambda i: CATEGORIES[i]["label"],
        horizontal=True,
        label_visibility="collapsed",
    )
    selected_trace = CATEGORIES[cat_idx]["trace"]
    st.markdown('<div style="height:0.75rem;"></div>', unsafe_allow_html=True)

    # Query header — quoted question style, neutral colors
    elast = selected_trace["elasticity"]
    status_pill = (pill("Multicollinearity", "warn")
                   if elast["multicollinearity_warning"]
                   else pill("Stable", "success"))
    sig_pill = (pill("p < 0.05", "success")
                if elast["p_value"] < 0.05
                else pill("Not significant", "warn"))
    st.markdown(
        f'<div style="margin: 0.25rem 0 1.25rem 0;">'
        f'<div style="font-size: 0.72rem; color: var(--fg-tertiary); '
        f'text-transform:uppercase; letter-spacing:0.08em; font-weight:500; '
        f'margin-bottom:0.4rem;">User query</div>'
        f'<div style="font-size: 1.35rem; font-weight: 500; color: var(--fg-primary); '
        f'letter-spacing:-0.02em; line-height:1.35;">'
        f'{selected_trace["query"]}</div>'
        f'<div style="color: var(--fg-secondary); margin-top:0.55rem; font-size:0.85rem;">'
        f'Mapped to <code style="color:var(--accent);background:var(--accent-soft);'
        f'padding:0.1rem 0.4rem;border-radius:4px;font-size:0.8rem;">'
        f'{selected_trace["category_pt"].replace("_", " ")}</code> '
        f'<span style="color:var(--fg-tertiary);">'
        f'({selected_trace["category_en"].replace("_", " ")})</span> &nbsp;'
        f'{status_pill} {sig_pill}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # ── Recommendation (lead with the answer) ────────────────
    section_header("", "What we recommend")
    render_recommendation_cards(selected_trace)
    st.plotly_chart(plot_revenue_scenarios(
        selected_trace["scenarios"], selected_trace["current"]
    ), use_container_width=True)
    render_causal_caveat()

    # ── Reasoning transparency (per assignment §2 rubric) ────
    section_header("", "How the agent got here")
    render_trace_steps(selected_trace)
    if selected_trace["elasticity"]["multicollinearity_warning"]:
        st.warning(
            f"**Multicollinearity detected** — controlled β = "
            f"{selected_trace['elasticity']['controlled_beta']}, "
            f"naive β = {selected_trace['elasticity']['naive_beta']}. "
            f"The agent auto-fell-back to the naive estimate."
        )
    with st.expander("Read the agent's full written answer"):
        st.markdown(selected_trace["final_answer"])


# ── Tab 2: Live Agent ────────────────────────────────────────
with tab2:
    section_header("", "Run the live agent against the Anthropic API")
    st.info(
        "This tab requires `ANTHROPIC_API_KEY`, `KAGGLE_API_TOKEN`, and "
        "`OPENWEATHER_API_KEY` in `.streamlit/secrets.toml` or env vars. "
        "Use the **Cached demo** tab if you don't have keys configured."
    )

    st.caption(
        "Try: *Should we discount garden tools by 10% next month?* · "
        "*What if we raise sports gear prices by 15%?* · "
        "*How elastic are bed sheets?*"
    )
    user_q = st.text_area(
        "Ask a pricing question",
        value="Should we discount garden tools by 10% next month?",
        height=80,
        placeholder="e.g. Should we discount garden tools by 10% next month?",
    )

    # Layout: planner-version radio is wider than the run button
    col_v, col_run = st.columns([3, 1])
    with col_v:
        v = st.radio(
            "Planner version", ["v2 (production)", "v1 (Shortcut Bias demo)"],
            horizontal=True, label_visibility="collapsed",
        )
    planner_version = "v1" if "v1" in v else "v2"

    if col_run.button("Run agent", type="primary", use_container_width=True):
        with st.spinner("Planner reasoning…"):
            try:
                import os
                # Load secrets from streamlit if available
                for key in ["ANTHROPIC_API_KEY", "KAGGLE_API_TOKEN", "OPENWEATHER_API_KEY"]:
                    if key in st.secrets:
                        os.environ[key] = st.secrets[key]
                if not os.environ.get("ANTHROPIC_API_KEY"):
                    st.error(
                        "**Missing `ANTHROPIC_API_KEY`** — add it to "
                        "`.streamlit/secrets.toml` (or set as env var) and reload. "
                        "Tip: switch to the **Cached demo** tab to explore without keys."
                    )
                else:
                    import anthropic
                    from priceiq_agent import priceiq_agent
                    client = anthropic.Anthropic()
                    result = priceiq_agent(user_q, client, verbose=False, planner_version=planner_version)

                    st.success(
                        f"Agent finished in **{result['telemetry']['latency_s']:.1f}s** "
                        f"({result['telemetry']['iterations']} iterations · "
                        f"{len(result['telemetry']['tool_calls'])} tool calls)"
                    )
                    st.markdown(f"**Plan**: `{result['plan']}`")
                    st.markdown("---")
                    section_header("", "Final answer")
                    st.markdown(result["answer"])
                    render_causal_caveat()
                    with st.expander("Full telemetry"):
                        st.json(result["telemetry"])
            except ImportError:
                st.error(
                    "**`anthropic` package not installed.** Run "
                    "`pip install anthropic` then refresh."
                )
            except Exception as e:
                st.error(
                    f"**Agent run failed** — `{type(e).__name__}: {e}`. "
                    f"Common causes: invalid API key, Olist data not yet downloaded "
                    f"(first run downloads ~50MB), or OpenWeather key not yet active "
                    f"(takes ~1 hour after creation)."
                )


# ════════════════════════════════════════════════════════════
# FOOTER
# ════════════════════════════════════════════════════════════
st.markdown('<div style="height:2.5rem;"></div>', unsafe_allow_html=True)
st.markdown(
    '<div class="footer">'
    '<div>'
    '<b style="color:var(--fg-primary);">PriceIQ</b> · '
    'JHU Carey · Generative AI · Phase 2 · 2026-05'
    '</div>'
    '<div>'
    '<a href="https://github.com/miyutakatsuki/priceiq-agent/blob/main/Phase2_Final_Report.md" target="_blank" rel="noopener">Final report</a> &nbsp;·&nbsp; '
    '<a href="https://github.com/miyutakatsuki/priceiq-agent#readme" target="_blank" rel="noopener">Demo video</a> &nbsp;·&nbsp; '
    '<a href="https://github.com/miyutakatsuki/priceiq-agent" target="_blank" rel="noopener">GitHub</a> &nbsp;·&nbsp; '
    '<a href="https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce" '
    'target="_blank" rel="noopener">Olist data</a>'
    '</div>'
    '<div>Sun · Cheng · Li</div>'
    '</div>',
    unsafe_allow_html=True,
)
