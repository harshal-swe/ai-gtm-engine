#!/bin/bash
# Run the GTM Gym Harbor benchmark on Tenki: oracle plus replayed model answers.
# Usage: harbor/run_bench.sh <job-name> [samples.jsonl]   (no samples file = oracle)
set -euo pipefail
cd "$(dirname "$0")/.."
export PATH="$HOME/.local/bin:$PATH"
set -a; [ -f .env ] && . ./.env; set +a
name=$1; samples=${2:-}
if [ -z "$samples" ]; then agent=(--agent oracle); else agent=(--agent replay_agent:ReplayAgent); fi
PYTHONPATH=harbor GTMGYM_SAMPLES="$PWD/${samples}" harbor run -p harbor/tasks -e tenki_harbor:TenkiEnvironment \
  "${agent[@]}" -n "${N_CONCURRENT:-2}" -r 3 --retry-include QuotaExceededError --retry-include RuntimeError -o harbor/jobs --job-name "$name"
