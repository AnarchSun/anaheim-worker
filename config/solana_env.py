# PATH: src/config/solana_env.py
import os
from dotenv import load_dotenv

# Charger automatiquement .env.local à la racine du projet
load_dotenv(dotenv_path=os.path.join, verbose=True)