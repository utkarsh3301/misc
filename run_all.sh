#!/usr/bin/env bash
# Run every analysis, then the unit tests (some compare an independent recomputation with results/), then the figures.
# From the repo root: bash run_all.sh
set -euo pipefail
export PYTHONPATH=.
mkdir -p results/logs results/figures/data
for s in run_vrp_study run_vrp_robustness run_tail_frequency run_variance_by_session run_rolling_verifiability \
         run_conditional_rules run_power_analysis run_event_check run_published_stats_arithmetic run_data_audit; do
  echo "=== ${s}"
  python3 "scripts/${s}.py" > "results/logs/${s}.txt"
done
python3 -m unittest discover -s tests
python3 scripts/make_figures.py
echo "done"
