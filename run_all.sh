#!/usr/bin/env bash
# Run the unit tests, every analysis and the figure builder. From the repo root: bash run_all.sh
set -euo pipefail
export PYTHONPATH=.
mkdir -p results/logs results/figures/data
python3 -m unittest discover -s tests
for s in run_vrp_study run_vrp_robustness run_tail_frequency run_variance_by_session run_rolling_verifiability \
         run_conditional_rules run_power_analysis run_event_check run_published_stats_arithmetic; do
  echo "=== ${s}"
  python3 "scripts/${s}.py" > "results/logs/${s}.txt"
done
python3 scripts/make_figures.py
echo "done"
