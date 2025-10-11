# Anaheim Worker

Anaheim Worker est le moteur central d’autogestion et d’autofix de votre projet **anarcrypt.sol**.  
Il combine gestion Git, patches TypeScript, simulation LLM et hot reload pour automatiser le développement et le debugging.

---

## Chemin du projet

Par défaut, le chemin du projet est :

path: /home/anarchsun/RustroverProjects/anarcrypt.sol/anaheim-worker


Ce chemin est utilisé dans le code comme `PROJECT_PATH` et sert de racine pour :

- les scripts TypeScript,
- les logs et diagnostics (`diagnostics/`),
- le hot reload,
- les commits automatiques vers les branches `Orion` et `FLOOD`.

---

## Structure des modules

Le dossier `src/workers/modules/` contient :

| Module | Description |
|--------|------------|
| `anaheim_worker_safe.py` | Worker sécurisé (safe) pour le développement et l’autofix. |
| `anarcrypt_worker_debug.py` | Mode debug / dry-run : simule l’application des patches TS et la collecte d’erreurs sans commit. |
| `hyper_optimal_worker.py` | Version optimisée multi-thread pour exécuter rapidement les cycles TS / LLM / Git. |
| `worker_fastloop.py` | Boucle rapide pour testing, avec simulation LLM et Playwright. |
| `anarcrypt_worker_hyper.py` | Hyper-worker prêt pour production : multi-thread, auto-fix, hot reload, flush vers FLOOD branch. |

---

## Fonctions centrales exposées

- `PROJECT_PATH` : chemin du projet.
- `repo_open()` : ouvre le dépôt Git.
- `apply_ts_actions(actions)` : applique les patches TypeScript.
- `handle_ts_error(err)` : gère un TS error via `apply_ts_actions`.
- `auto_ts_fix_cycle_safe(...)` : cycle automatique de corrections TS.
- `log(msg)` : log interne dans le terminal et fichier.

---

## Branches Git

- `Orion` : branche principale pour les actions TS.
- `Orion-Exploration` : branche d’exploration / tests.
- `<flood>` : branche consolidée pour flush des commits, limitée à 250 commits.

---

## Logs et diagnostics

- `diagnostics/` : contient `copilot_delegations.log` et autres fichiers de debug.
- `worker_safe.log` / `hyper_worker.log` : logs des workers.

---

## Installation / Pré-requis

1. Cloner le projet :
```bash
git clone https://github.com/votre-repo/anarcrypt.sol.git
cd anarcrypt.sol/anaheim-worker