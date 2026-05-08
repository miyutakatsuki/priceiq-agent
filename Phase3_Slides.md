---
marp: true
paginate: true
size: 16:9
theme: default
style: |
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');
  :root {
    --accent:    #DC2626;
    --fg:        #09090B;
    --fg-2:      #52525B;
    --fg-3:      #A1A1AA;
    --border:    #E4E4E7;
    --bg:        #FFFFFF;
    --bg-mute:   #FAFAFA;
  }
  section {
    font-family: 'Inter', -apple-system, sans-serif;
    color: var(--fg);
    background: var(--bg);
    padding: 90px 110px 70px 110px;
    font-size: 22px;
    letter-spacing: -0.011em;
    font-weight: 400;
  }
  section::after {
    color: var(--fg-3);
    font-family: 'JetBrains Mono', monospace;
    font-size: 12px;
    bottom: 28px; right: 110px;
  }
  h1 {
    font-size: 72px; font-weight: 600;
    letter-spacing: -0.035em; line-height: 1.05;
    margin: 0 0 8px 0; color: var(--fg);
  }
  h2 {
    font-size: 44px; font-weight: 600;
    letter-spacing: -0.025em; line-height: 1.15;
    margin: 0 0 32px 0; color: var(--fg);
  }
  h3 {
    font-size: 13px; font-weight: 500;
    color: var(--fg-3); text-transform: uppercase;
    letter-spacing: 0.12em; margin: 0 0 16px 0;
  }
  p, li {
    color: var(--fg-2); line-height: 1.55;
    font-size: 22px; font-weight: 400;
  }
  strong { color: var(--fg); font-weight: 500; }
  em     { color: var(--fg-2); font-style: normal; }
  code {
    font-family: 'JetBrains Mono', monospace;
    background: var(--bg-mute);
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 19px;
    color: var(--accent);
    font-weight: 500;
  }
  hr { border: 0; height: 1px; background: var(--border); margin: 32px 0; }
  ul { padding-left: 24px; margin: 0; }
  li { margin: 8px 0; }
  /* layout helpers */
  .eyebrow {
    color: var(--accent);
    font-size: 13px; font-weight: 600;
    text-transform: uppercase; letter-spacing: 0.14em;
    margin-bottom: 24px;
  }
  .lead {
    font-size: 28px; font-weight: 400;
    color: var(--fg-2); line-height: 1.45;
    max-width: 900px;
  }
  .display-num {
    font-size: 96px; font-weight: 600;
    color: var(--fg); letter-spacing: -0.04em;
    font-feature-settings: 'tnum'; line-height: 1;
  }
  .display-num.accent { color: var(--accent); }
  .num-grid {
    display: grid; grid-template-columns: 1fr 1fr 1fr;
    gap: 64px; margin-top: 12px;
  }
  .num-grid .label {
    font-size: 13px; font-weight: 500;
    color: var(--fg-3); text-transform: uppercase;
    letter-spacing: 0.12em; margin-bottom: 14px;
  }
  .num-grid .num {
    font-size: 64px; font-weight: 600;
    color: var(--fg); letter-spacing: -0.03em;
    font-feature-settings: 'tnum'; line-height: 1;
  }
  .num-grid .num.accent { color: var(--accent); }
  .num-grid .meta {
    font-size: 16px; color: var(--fg-2);
    margin-top: 12px; line-height: 1.4;
  }
  .col-2 {
    display: grid; grid-template-columns: 1fr 1fr;
    gap: 72px; margin-top: 12px;
  }
  .col-2 h3 { margin-bottom: 12px; }
  .col-2 .body { font-size: 20px; color: var(--fg-2); line-height: 1.55; }
  .col-2 .body strong { color: var(--fg); }
  .footnote {
    font-size: 14px; color: var(--fg-3);
    margin-top: 40px; line-height: 1.5;
  }
  .accent-rule {
    width: 48px; height: 2px;
    background: var(--accent);
    margin: 0 0 24px 0;
  }
  .stack {
    font-family: 'JetBrains Mono', monospace;
    font-size: 18px; line-height: 1.85;
    color: var(--fg-2);
  }
  .stack .key { color: var(--fg); font-weight: 500; }
  .stack .arrow { color: var(--fg-3); }
  .meta-line {
    font-size: 16px; color: var(--fg-3);
    font-feature-settings: 'tnum';
    margin-top: 20px;
  }
---

<!-- _paginate: false -->
<!-- _class: cover -->

<div class="eyebrow">JHU Carey · Generative AI · Phase 3</div>

# PriceIQ

<p class="lead">A pricing decision agent grounded in 100,000 real e-commerce orders.</p>

<div class="meta-line">Kangchun Sun &middot; Tao Cheng &middot; Maoyuan Li &nbsp;·&nbsp; 2026</div>

---

<div class="eyebrow">The problem</div>

<h2>A correct pricing answer needs four kinds of evidence the LLM cannot fabricate.</h2>

<div class="col-2">
<div>
<h3>Quantitative</h3>
<div class="body">
Price elasticity β with a confidence interval — measured, not guessed.
</div>
</div>
<div>
<h3>Contextual</h3>
<div class="body">
Holiday proximity. Weather. Seasonality. Each is a separate signal.
</div>
</div>
</div>

<div class="footnote">A single prompt cannot run OLS. A multi-step agent with typed tools can.</div>

---

<div class="eyebrow">Architecture</div>

<h2>Two agents, five tools, one kill switch.</h2>

<div class="stack">
<span class="key">Planner</span>  <span class="arrow">·</span>  Sonnet 4.5  <span class="arrow">·</span>  XML few-shot, 5 worked examples<br>
<span class="key">Executor</span> <span class="arrow">·</span>  Haiku 4.5   <span class="arrow">·</span>  manual <code>tool_use</code> loop, MAX_ITER = 8<br>
<span class="key">Tools</span>    <span class="arrow">·</span>  SQL  <span class="arrow">→</span>  OLS  <span class="arrow">→</span>  Demand  <span class="arrow">→</span>  Weather  <span class="arrow">→</span>  Simulator<br>
<span class="key">Output</span>   <span class="arrow">·</span>  recommendation + verbatim causal caveat
</div>

<div class="footnote">Sonnet plans, Haiku executes. <strong>$0.029 / query</strong> &mdash; 53% cheaper than all-Sonnet, 22 pts more accurate than all-Haiku.</div>

---

<div class="eyebrow">Live demo · garden tools −10%</div>

<div class="display-num accent">+33%</div>

<p class="lead" style="margin-top:24px;">Central revenue lift, with 95% CI <strong>+21% to +46%</strong>.</p>

<div class="footnote">
β = −2.83 · Mother's Day demand × 1.16 · rain headwind × 0.94 · simulator integrates β CI into 3 scenarios.<br>
6 iterations · 31 seconds · $0.029. <em>The agent's recommendation pastes the causal caveat verbatim.</em>
</div>

---

<div class="eyebrow">Reasoning rigor · Prompt Version Control</div>

<h2>Same query, two prompts.</h2>

<div class="col-2">
<div>
<h3>v1</h3>
<div class="body">
<strong>3 of 5 tools called.</strong><br>
Plan skips demand and weather.<br>
Final answer is correct in direction but missing context.<br>
<br>
<em>Shortcut Bias.</em>
</div>
</div>
<div>
<h3>v2</h3>
<div class="body">
<strong>5 of 5 tools called.</strong><br>
Same query, +5 worked examples + 11-category list in the prompt.<br>
Plan completes the full pipeline.<br>
<br>
<em>+45% cost &mdash; complete context.</em>
</div>
</div>
</div>

<div class="footnote">In agent design, the prompt is not a hint &mdash; it's a contract. Without examples, the LLM honors the letter of the spec but not the intent.</div>

---

<div class="eyebrow">Evaluation · 50 cases · LLM-as-Judge · 3-run consistency</div>

<div class="num-grid">
<div>
<div class="label">Pass rate</div>
<div class="num accent">92%</div>
<div class="meta">46 of 50 · avg judge score 4.3 / 5</div>
</div>
<div>
<div class="label">Cost / pass</div>
<div class="num">$0.029</div>
<div class="meta">vs $0.062 all-Sonnet · vs $0.016 all-Haiku at 76% pass</div>
</div>
<div>
<div class="label">Category consistency</div>
<div class="num">97%</div>
<div class="meta">Sonnet maps the same query to the same category across 3 runs</div>
</div>
</div>

<div class="footnote">Multicollinearity warning surface rate: <strong>100%</strong> on relevant cases. Causal caveat: included on every successful run.</div>

---

<div class="eyebrow">Honest failures</div>

<h2>Six logged. Four fixed in this phase.</h2>

<div class="col-2">
<div>
<h3>Fixed</h3>
<div class="body">
<strong>F-01</strong>  Memory threshold confused mid-loop &mdash; raised 8K → 30K + explicit "finalize NOW" instruction.<br><br>
<strong>F-02</strong>  Multicollinearity flipped β sign &mdash; reduced 7 predictors to 2, added diagnostic.
</div>
</div>
<div>
<h3>Open · acknowledged</h3>
<div class="body">
<strong>F-06</strong>  Out-of-scope query <em>"weather in Tokyo?"</em> mapped to <code>telefonia</code> instead of refusing. Tool 1's <code>found: False</code> recovered the run; ~$0.005 wasted.<br><br>
<em>Fix in v3 prompt &mdash; deferred.</em>
</div>
</div>
</div>

<div class="footnote">Full log: <code>Failure_Log_Phase2.md</code> &middot; red-team findings: RT-01..RT-04 in <code>Phase2_Final_Report.md</code> §5.</div>

---

<!-- _paginate: false -->

<div class="eyebrow">Thank you</div>

# Questions?

<div class="accent-rule" style="margin-top:48px;"></div>

<div class="stack" style="margin-top:32px;">
<span class="key">repo</span>  <span class="arrow">·</span>  22 files  <span class="arrow">·</span>  9 .py + 10 .md + 2 .json + 1 .ipynb<br>
<span class="key">demo</span>  <span class="arrow">·</span>  <code>streamlit run app.py</code><br>
<span class="key">eval</span>  <span class="arrow">·</span>  <code>eval_suite.run_full_eval(n=50, consistency_runs=3)</code>
</div>

<div class="meta-line" style="margin-top:48px;">Sun &middot; Cheng &middot; Li &nbsp;·&nbsp; JHU Carey &middot; Generative AI &middot; 2026</div>
