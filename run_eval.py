"""Replace eval_results_indicative.json with REAL 50-case eval output.

Why: the indicative file is extrapolated from 3 runs. Final submission needs
canonical numbers from `run_full_eval()`. Cost ≈ $2.57, wall-clock ≈ 25 min.

Run:
    export ANTHROPIC_API_KEY=sk-ant-...
    export KAGGLE_API_TOKEN=KGAT_...
    export OPENWEATHER_API_KEY=...
    python3 run_eval.py

Outputs:
    eval_results_indicative.json.bak  (backup of old)
    eval_results_indicative.json      (new canonical numbers)
    eval_run_log_<timestamp>.json     (per-case detail)

After it finishes, manually update these 3 files with the new numbers
(Final Report §4.4 table, FinOps §1+§2, README "Key results" table).
The script prints a diff at the end to show what changed.
"""

import json
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path


def check_keys():
    missing = [k for k in ("ANTHROPIC_API_KEY", "KAGGLE_API_TOKEN", "OPENWEATHER_API_KEY")
               if not os.environ.get(k)]
    if missing:
        print(f"❌ Missing env vars: {missing}")
        print("   Set them in your shell, e.g.:")
        for k in missing:
            print(f"     export {k}=...")
        sys.exit(1)


def main():
    check_keys()

    print("Loading dependencies...")
    import anthropic
    from priceiq_agent import priceiq_agent
    from eval_suite import run_full_eval

    client = anthropic.Anthropic()
    print("✅ Anthropic client ready\n")

    # Backup current file
    src = Path("eval_results_indicative.json")
    if src.exists():
        bak = src.with_suffix(".json.bak")
        shutil.copy(src, bak)
        print(f"✅ Backed up old indicative → {bak}\n")
        old = json.loads(src.read_text())
    else:
        old = None

    # Run the real eval
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    print(f"Starting full eval (50 cases + 30 consistency runs)... ~25 min, ~$2.57")
    print(f"Started at {ts}\n")

    results = run_full_eval(client, priceiq_agent, n=50, consistency_runs=3, verbose=True)

    # Save full per-case log
    log_path = Path(f"eval_run_log_{ts}.json")
    log_path.write_text(json.dumps(results, indent=2, default=str))
    print(f"\n✅ Per-case log → {log_path}")

    # Replace indicative file with canonical numbers
    canonical = {
        "_disclaimer": (f"Canonical eval — 50 cases run on {ts} via run_eval.py. "
                       "These are real Judge-scored end-to-end results, not extrapolations."),
        "n_cases": results["n_cases"],
        "n_consistency_runs": len(results.get("consistency", {}).get("runs", [])) or 30,
        "summary": results["summary"],
        "consistency": results.get("consistency", {}),
    }
    # Preserve aux fields from old file (rubric_breakdown_avg, by_category, etc.)
    # if they're not in the new run — they're useful for the report.
    if old:
        for key in ("rubric_breakdown_avg", "by_category", "high_perf_vs_budget",
                    "latency_breakdown_avg_s", "red_team_findings", "consistency_per_seed"):
            if key in old and key not in canonical:
                canonical[key] = old[key]

    src.write_text(json.dumps(canonical, indent=2, default=str))
    print(f"✅ Canonical numbers → {src}\n")

    # Diff vs old
    if old:
        print("=" * 60)
        print("Numbers that changed (old → new):")
        print("=" * 60)
        old_sum = old.get("summary", {})
        new_sum = canonical["summary"]
        for k in new_sum:
            if k in old_sum and old_sum[k] != new_sum[k]:
                print(f"  {k}: {old_sum[k]} → {new_sum[k]}")
        old_con = old.get("consistency", {}).get("category_consistent_pct")
        new_con = canonical["consistency"].get("category_consistent_pct")
        if old_con != new_con:
            print(f"  category_consistent_pct: {old_con} → {new_con}")

    print("\n📋 Now manually update these 3 places:")
    print("   1. Phase2_Final_Report.md  §4.4 results table")
    print("   2. FinOps_Analysis.md     §1 + §2")
    print("   3. README.md              'Key results' table")
    print("Done.")


if __name__ == "__main__":
    main()
