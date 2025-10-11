#!/bin/bash
# clean_workers.sh
# Usage: ./clean_workers.sh

set -e

echo "🧹 Nettoyage du repo Anaheim Worker..."

# 1️⃣ Supprimer tous les anciens workers legacy sauf modules
echo "📂 Suppression des anciens workers dans workers/legacy..."
find src/workers/legacy/ -type f -not -path "src/workers/legacy/modules/*" -exec rm -v {} +

# 2️⃣ Supprimer __pycache__ partout
echo "🗑️ Suppression des caches Python (__pycache__ et .pyc)..."
find src/ -name "__pycache__" -exec rm -rf {} +
find src/ -name "*.pyc" -delete

# 3️⃣ Vérifier que modules restent intacts
echo "✅ Modules conservés :"
ls -1 src/workers/modules/

# 4️⃣ Nettoyage des anciens logs et diagnostics
echo "🧾 Nettoyage des anciens logs..."
rm -f src/workers/worker.log
rm -rf src/workers/diagnostics/*

# 5️⃣ Vérification
echo "🔍 Vérification structure finale des workers:"
tree -L 3 src/workers/

echo "🎯 Nettoyage terminé. Repo prêt avec modules et hyper_optimal_worker.py"
