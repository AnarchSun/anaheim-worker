#!/bin/bash
set -e
# Usage: ./setup_worker.sh /path/to/project
PROJECT_PATH=${1:-../anaheim-putsch-self-governance-solana-dapp}
DATA_DIR=$(pwd)/data

mkdir -p "$DATA_DIR"
mkdir -p logs

echo "Creating data dir: $DATA_DIR"

# If repo not present, fail
if [ ! -d "$PROJECT_PATH" ]; then
  echo "ERROR: project path not found: $PROJECT_PATH"
  exit 1
fi

# Copy sample config
cp config/worker_config.yml "$DATA_DIR"/worker_config.yml || true

echo "Done. To run via docker-compose: cd docker && docker compose up --build -d"
