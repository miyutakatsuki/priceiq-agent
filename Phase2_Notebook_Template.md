# Phase 2 Colab Notebook — assembly template

> The Phase 2 deliverable expects ONE Colab notebook with telemetry scaffolding.
> Rather than checking in a half-broken Untitled4 from development, this template
> tells the team how to assemble the canonical notebook from local Python modules.

## Recipe

Open Colab → New Notebook. Add these cells in order:

### Cell 1 — Secrets + dependencies
```python
import os
from google.colab import userdata
os.environ['ANTHROPIC_API_KEY']  = userdata.get('ANTHROPIC_API_KEY')
os.environ['KAGGLE_API_TOKEN']   = userdata.get('KAGGLE_API_TOKEN')
os.environ['OPENWEATHER_API_KEY']= userdata.get('OPENWEATHER_API_KEY')

!pip install -q anthropic kagglehub statsmodels
```

### Cells 2-7 — Write each module (one cell per file, use `%%writefile`)

| Cell | File | Depends on |
|---|---|---|
| 2 | `priceiq_data.py` | — (kagglehub only) |
| 3 | `priceiq_elasticity.py` | Tool 1 |
| 4 | `priceiq_demand.py` | Tool 1 |
| 5 | `priceiq_weather.py` | — (OpenWeather only) |
| 6 | `priceiq_simulator.py` | Tools 1, 2, 3, 5 |
| 7 | `priceiq_agent.py` | All 5 tools |

Each cell starts with `%%writefile <filename>` then the file contents.
Run cells **in order** so imports resolve.

### Cell 8 — End-to-end demo
```python
import importlib, sys
for m in ['priceiq_data','priceiq_elasticity','priceiq_demand',
          'priceiq_weather','priceiq_simulator','priceiq_agent']:
    if m in sys.modules: importlib.reload(sys.modules[m])

import anthropic
from priceiq_agent import priceiq_agent
client = anthropic.Anthropic()

result = priceiq_agent(
    "Should we discount garden tools by 10% next month?",
    client, verbose=True, planner_version="v2",
)
print(result["answer"])
```

### Cell 9 — 50-case evaluation (optional, ~$2.57, ~25 min wall-clock)
```python
from eval_suite import run_full_eval  # also %%writefile this module first
results = run_full_eval(client, priceiq_agent, n=50, consistency_runs=3)
import json; print(json.dumps(results["summary"], indent=2))
```

> Cell 9 is **synchronous** — it runs 50 + 30 = 80 agent invocations sequentially.
> Plan for ~25 minutes. If Colab disconnects, restart and replay only Cells 1–8
> + the eval cell; module files (`%%writefile`) persist in the runtime FS.

### Cell 10 — Telemetry export
```python
import json, pathlib
out = pathlib.Path('telemetry.json')
out.write_text(json.dumps(result['telemetry'], indent=2, default=str))
print(f"Saved telemetry to {out.absolute()}")
```

---

## Why a template, not a checked-in `.ipynb`

`%%writefile` cells get long (5 of them are 100+ lines each). A live notebook
that round-trips through GitHub diffs poorly. The local `priceiq_*.py` modules
are the source of truth; the notebook is just a thin wrapper for Colab's
runtime.

When submitting, run all cells in order, save as `PriceIQ_Phase2_Final.ipynb`,
and include alongside the local modules.
