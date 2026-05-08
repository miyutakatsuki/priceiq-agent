"""Assemble PriceIQ_Phase2_Final.ipynb from local priceiq_*.py modules.

Re-run this whenever any priceiq_*.py changes — Streamlit Cloud reads from
disk, but Colab grader reads the .ipynb so the embedded copies must match.

    python3 build_ipynb.py
"""

import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent


def code_cell(src: str) -> dict:
    return {
        "cell_type": "code", "execution_count": None,
        "metadata": {}, "outputs": [],
        "source": src.splitlines(keepends=True),
    }


def md_cell(src: str) -> dict:
    return {
        "cell_type": "markdown", "metadata": {},
        "source": src.splitlines(keepends=True),
    }


def writefile_cell(filename: str) -> dict:
    body = (ROOT / filename).read_text()
    return code_cell(f"%%writefile {filename}\n{body}")


cells = [
    md_cell(
        "# PriceIQ — Phase 2 Final Notebook\n\n"
        "Track B (Claude Agent SDK) · Sonnet Planner + Haiku Executor + 5 typed tools.\n\n"
        "**Run order**: cells 1 → 10. Cell 9 (full 50-case eval) is optional and "
        "costs ~$2.57 — comment it out if you only want the demo.\n\n"
        "**Secrets**: Set `ANTHROPIC_API_KEY`, `KAGGLE_API_TOKEN`, "
        "`OPENWEATHER_API_KEY` in Colab → Secrets panel before running.\n\n"
        "Source: built from local priceiq_*.py via `build_ipynb.py`. "
        "Re-run that script after any module change.\n"
    ),
    md_cell("## Cell 1 — Secrets + dependencies"),
    code_cell(
        "import os\n"
        "try:\n"
        "    from google.colab import userdata\n"
        "    os.environ['ANTHROPIC_API_KEY']   = userdata.get('ANTHROPIC_API_KEY')\n"
        "    os.environ['KAGGLE_API_TOKEN']    = userdata.get('KAGGLE_API_TOKEN')\n"
        "    os.environ['OPENWEATHER_API_KEY'] = userdata.get('OPENWEATHER_API_KEY')\n"
        "except ImportError:\n"
        "    # Local run — assume env vars already set\n"
        "    pass\n"
        "\n"
        "!pip install -q anthropic kagglehub statsmodels plotly\n"
    ),
    md_cell(
        "## Cells 2–7 — Module sources via `%%writefile`\n\n"
        "Each cell writes one module to the runtime filesystem. Run in order so imports resolve."
    ),
    md_cell("### Cell 2 — Tool 1 (`priceiq_data.py`) · Olist SQLite SQL"),
    writefile_cell("priceiq_data.py"),
    md_cell("### Cell 3 — Tool 2 (`priceiq_elasticity.py`) · log-log OLS + multicollinearity"),
    writefile_cell("priceiq_elasticity.py"),
    md_cell("### Cell 4 — Tool 3 (`priceiq_demand.py`) · BR holidays + seasonality"),
    writefile_cell("priceiq_demand.py"),
    md_cell("### Cell 5 — Tool 5 (`priceiq_weather.py`) · OpenWeather 5-day forecast"),
    writefile_cell("priceiq_weather.py"),
    md_cell("### Cell 6 — Tool 4 (`priceiq_simulator.py`) · 3-scenario revenue projection"),
    writefile_cell("priceiq_simulator.py"),
    md_cell("### Cell 7 — Agent (`priceiq_agent.py`) · TOOLS schema + Planner v1/v2 + Executor loop"),
    writefile_cell("priceiq_agent.py"),
    md_cell("## Cell 8 — End-to-end demo"),
    code_cell(
        "import importlib, sys\n"
        "for m in ['priceiq_data','priceiq_elasticity','priceiq_demand',\n"
        "          'priceiq_weather','priceiq_simulator','priceiq_agent']:\n"
        "    if m in sys.modules: importlib.reload(sys.modules[m])\n"
        "\n"
        "import anthropic\n"
        "from priceiq_agent import priceiq_agent\n"
        "client = anthropic.Anthropic()\n"
        "\n"
        "result = priceiq_agent(\n"
        "    'Should we discount garden tools by 10% next month?',\n"
        "    client, verbose=True, planner_version='v2',\n"
        ")\n"
        "print('\\n=== Final answer ===')\n"
        "print(result['answer'])\n"
    ),
    md_cell(
        "## Cell 9 — Optional: 50-case evaluation\n\n"
        "**Cost**: ~$2.57 (50 agent calls × $0.029 + 50 judge calls × $0.005 + "
        "30 consistency runs × $0.029). **Wall-clock**: ~25 min.\n\n"
        "Uncomment to run."
    ),
    code_cell(
        "# %%writefile eval_suite.py\n"
        "# (paste eval_suite.py contents here, then run the next cell)\n"
        "# from eval_suite import run_full_eval\n"
        "# results = run_full_eval(client, priceiq_agent, n=50, consistency_runs=3)\n"
        "# import json; print(json.dumps(results['summary'], indent=2))\n"
    ),
    md_cell("## Cell 10 — Telemetry export"),
    code_cell(
        "import json, pathlib\n"
        "out = pathlib.Path('telemetry.json')\n"
        "out.write_text(json.dumps(result['telemetry'], indent=2, default=str))\n"
        "print(f'Saved telemetry to {out.absolute()}')\n"
    ),
]

nb = {
    "cells": cells,
    "metadata": {
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python", "version": "3.11"},
        "colab": {"provenance": []},
    },
    "nbformat": 4, "nbformat_minor": 5,
}

if __name__ == "__main__":
    out_path = ROOT / "PriceIQ_Phase2_Final.ipynb"
    out_path.write_text(json.dumps(nb, indent=1, ensure_ascii=False))
    size_kb = out_path.stat().st_size // 1024
    print(f"✅ wrote {out_path.name}  ({len(cells)} cells, {size_kb}KB)")
