#!/bin/bash
set -e

# ----------------------------------------------
# 🧩 Anaheim Worker – Submodule Initialization Script
# ----------------------------------------------
# Auto-initialize + sync + branch checkout for all submodules
# Works with: governance, candy-machine, self-governance DApp
# ----------------------------------------------

GREEN="\033[1;32m"
YELLOW="\033[1;33m"
BLUE="\033[1;34m"
MAGENTA="\033[1;35m"
RESET="\033[0m"

timestamp() {
  date +"%Y-%m-%d %H:%M:%S"
}

echo -e "${BLUE}[$(timestamp)] ⚙️ Initializing Anaheim submodules...${RESET}"

# Ensure we're at repo root
cd "$(dirname "$0")/.." || exit 1

# Make sure git detects the submodules listed in .gitmodules
echo -e "${YELLOW}→ Running git submodule init${RESET}"
git submodule init

# Update + recursively pull all nested submodules
echo -e "${YELLOW}→ Running git submodule update --recursive --remote${RESET}"
git submodule update --recursive --remote

# Show current status
echo -e "${MAGENTA}→ Checking submodule status...${RESET}"
git submodule status

# Switch to main/Orion branches for known modules
if [ -d "anaheim-worker/candy-machine/.git" ]; then
  echo -e "${YELLOW}→ Switching candy-machine to 'main' branch${RESET}"
  (cd anaheim-worker/candy-machine && git checkout main || true)
fi

if [ -d "anaheim-worker/governance/.git" ]; then
  echo -e "${YELLOW}→ Switching governance to 'Orion' branch${RESET}"
  (cd anaheim-worker/governance && git checkout Orion || git checkout main || true)
fi

if [ -d "anaheim-putsch-self-governance-solana-dapp/.git" ]; then
  echo -e "${YELLOW}→ Ensuring self-governance dApp is on 'main' branch${RESET}"
  (cd anaheim-putsch-self-governance-solana-dapp && git checkout main || true)
fi

# Commit the initialized state
git add .gitmodules anaheim-worker/candy-machine anaheim-worker/governance anaheim-putsch-self-governance-solana-dapp || true
git commit -m "Initialize and sync submodules [auto]" || echo -e "${YELLOW}No new changes to commit.${RESET}"

echo -e "${GREEN}✅ Submodules initialized, synced, and branches checked out.${RESET}"
echo -e "${BLUE}You can now run:${RESET}"
echo -e "${MAGENTA}   ./scripts/init_submodules.sh${RESET} anytime to re-sync your modules."
