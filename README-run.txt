1) placer ce dossier anaheim-worker/ à côté de ton repo anaheim-putsch...
2) modifier config/worker_config.yml si besoin (REPO path, thresholds)
3) exporter GITHUB_TOKEN si tu veux que le worker fasse des recherches (export GITHUB_TOKEN=...)
4) builder et lancer via docker-compose:
   cd anaheim-worker/docker
   docker compose up --build -d

alternativement lancer en local (si python & deps installées):
   pip install -r src/requirements.txt
   playwright install chromium
   python src/worker.py

# 1) personnaliser config:
edit config/worker_config.yml   # set repo_path to your project absolute path if desired

# 2) démarrer (docker recommended)
cd anaheim-worker/docker
docker compose up --build -d

# 3) logs
docker compose logs -f orion-worker

# 4) regarder fixes
cat data/fixes.json

pip install -r src/requirements.txt
playwright install chromium
python src/worker.py
