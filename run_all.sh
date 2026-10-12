#!/usr/bin/env bash
# Run every analysis, then the figure builder, then the unit tests. Some tests compare an independent
# recomputation with results/ and check that the numbers quoted in REPORT.md match results/, so they must run last.
# From the repo root: bash run_all.sh
set -euo pipefail
export PYTHONPATH=.
mkdir -p results/logs results/figures/data
for s in run_vrp_study run_vrp_robustness run_tail_frequency run_variance_by_session run_rolling_verifiability \
         run_conditional_rules run_power_analysis run_event_check run_published_stats_arithmetic run_data_audit; do
  echo "=== ${s}"
  python3 "scripts/${s}.py" > "results/logs/${s}.txt"
done
python3 scripts/make_figures.py
python3 -m unittest discover -s tests
echo "done"
