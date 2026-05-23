#!/usr/bin/env bash
# LEAP local setup — synthetic load cache and optional bundled parquet copies.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$REPO_ROOT"

echo "LEAP local setup"
echo "================"

python3 -m venv .venv 2>/dev/null || true
if [ -f .venv/bin/activate ]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

pip install -q -r requirements.txt

echo "Building synthetic load cache (90 days x 7 BAs)..."
python3 scripts/seed/seed_synthetic.py

if [ -f data/ELEC.parquet ]; then
  echo "Bundled data/ELEC.parquet present (plant-level EIA series)."
fi
if [ -f data/HIFLD_US_Electric_Power_Transmission_Lines_Complete.parquet ]; then
  echo "Bundled transmission parquet present."
fi

echo ""
echo "Setup complete. Run: python run.py"
echo "Dashboard: http://localhost:3000"
