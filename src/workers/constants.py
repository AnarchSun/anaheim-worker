# src/workers/constants.py
from pathlib import Path

# Base path du projet (racine du repo anaheim-worker)
PROJECT_ROOT = Path(__file__).resolve().parents[1]

# Fichier temporaire pour stocker les erreurs TS
TS_ERRORS_FILE = PROJECT_ROOT / "ts_errors.json"

# Répertoire où vivent les workers et modules
WORKERS_PATH = PROJECT_ROOT / "src" / "workers"

# Dossier pour logs ou fichiers d'état
LOGS_PATH = PROJECT_ROOT / "logs"

LOGS_PATH.mkdir(exist_ok=True)
