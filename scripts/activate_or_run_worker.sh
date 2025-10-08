#!/bin/bash
set -e

# ----------------------------
# 🔥 Anaheim Worker Launcher
# ----------------------------

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$PROJECT_DIR/.venv"
PYTHON="$VENV_DIR/bin/python"

"$PYTHON" "$PROJECT_DIR/src/worker_full.py"

# Crée .venv si absent
if [[ ! -d "$VENV_DIR" ]]; then
    echo -e "\033[1;34m[INFO] Création de l'environnement virtuel local (.venv)...\033[0m"
    python3 -m venv "$VENV_DIR"
fi

# Active l'environnement virtuel
echo -e "\033[1;32m[INFO] Activation de l'environnement virtuel...\033[0m"
source "$VENV_DIR/bin/activate"

# Installe les dépendances si requirements.txt existe
if [[ -f "$PROJECT_DIR/src/requirements.txt" ]]; then
    echo -e "\033[1;33m[INFO] Installation des dépendances...\033[0m"
    pip install --upgrade pip
    pip install -r "$PROJECT_DIR/src/requirements.txt"
fi

# Lance le worker
echo -e "\033[1;36m[INFO] Lancement du Anaheim Worker...\033[0m"
python "$PROJECT_DIR/src/worker_full.py"
