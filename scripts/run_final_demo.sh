#!/usr/bin/env bash
#
# run_final_demo.sh — IMAGINA V2.7 Final Demo Script
#
# Runs the complete fixture-based demo pipeline.
# Does NOT require real EEG or internet. Safe to run repeatedly.

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/backend"

echo "============================================"
echo "  IMAGINA V2.7 — Final Demo"
echo "============================================"
echo ""

echo "--- Dataset Manager List ---"
python3 -m app.cli.dataset_manager list
echo ""

echo "--- Dataset Evaluation ---"
python3 -m app.cli.dataset_eval \
  --dataset fixture \
  --max-windows 20 \
  --compute-pid-iqi \
  --compare fixture \
  --distribution-report \
  --export-features-csv
echo ""

echo "--- Dataset Quality ---"
python3 -m app.cli.dataset_quality \
  --dataset fixture \
  --max-windows 20
echo ""

echo "--- Product Demo ---"
python3 -m app.cli.product_demo
echo ""

echo "--- Scenario Runner ---"
python3 -m app.evaluation.scenario_runner \
  --scenario improving_user \
  --windows 20
echo ""

echo "--- Cohort Simulator ---"
python3 -m app.evaluation.cohort_simulator \
  --n 10 \
  --windows 20
echo ""

echo "============================================"
echo "  Final Demo Complete"
echo "============================================"
echo ""
echo "Outputs:"
echo "  data/exports/dataset_eval_fixture.json"
echo "  data/exports/dataset_distribution_fixture.json"
echo "  data/exports/dataset_features_fixture.csv"
echo "  data/exports/dataset_eval_compare_fixture_vs_fixture.json"
echo "  data/exports/dataset_quality_fixture.json"
echo "  data/exports/product_demo_report.json"
echo "  data/exports/product_demo_summary.md"
echo ""
echo "Frontend: http://localhost:3000/datasets"
echo "API: http://localhost:8000/api/datasets/catalog"
