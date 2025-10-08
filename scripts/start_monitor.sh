#!/bin/bash
set -e

# ----------------------------
# 🌌 Orion Chaos Operator Ultimate Monitoring
# ----------------------------

# Couleurs punk
RED="\033[1;31m"
GREEN="\033[1;32m"
YELLOW="\033[1;33m"
BLUE="\033[1;34m"
CYAN="\033[1;36m"
MAGENTA="\033[1;35m"
RESET="\033[0m"

# ---- Configs ----
CONTAINER_NAME="docker-orion-worker-1"
DOCKER_COMPOSE_PATH="/work/docker/docker-compose.yml"
CFG_PATH="/work/config/worker_config.yml"

# Discord setup
DISCORD_WEBHOOK=$(grep discord_webhook "$CFG_PATH" | awk '{print $2}')
DISCORD_SERVER_LINK="https://discord.gg/Dt7zvuFPGf"

# GitHub issue setup
GITHUB_REPO=$(grep github_repo "$CFG_PATH" | awk '{print $2}')
GITHUB_TOKEN=${GITHUB_TOKEN:-}

timestamp() {
    date +"%Y-%m-%d %H:%M:%S"
}

discord_alert() {
    local MESSAGE="$1"
    local TYPE="${2:-info}"
    [[ -z "$DISCORD_WEBHOOK" ]] && return
    curl -s -H "Content-Type: application/json" \
         -X POST \
         -d "{\"content\":\"[$(timestamp)] [$TYPE] $MESSAGE\"}" \
         "$DISCORD_WEBHOOK" >/dev/null 2>&1 || true
}

github_issue() {
    local TITLE="$1"
    local BODY="$2"
    [[ -z "$GITHUB_TOKEN" || -z "$GITHUB_REPO" ]] && return
    curl -s -H "Authorization: token $GITHUB_TOKEN" \
         -H "Accept: application/vnd.github.v3+json" \
         -X POST \
         -d "{\"title\": \"$TITLE\", \"body\": \"$BODY\"}" \
         "https://api.github.com/repos/$GITHUB_REPO/issues" >/dev/null 2>&1 || true
}

# ---- Vérifier ou créer config ----
if [[ ! -f "$CFG_PATH" ]]; then
    echo -e "${YELLOW}⚠️ Config introuvable, création par défaut: $CFG_PATH${RESET}"
    mkdir -p "$(dirname "$CFG_PATH")"
    cat > "$CFG_PATH" <<EOL
repo_path: /work/project
worker_branch: Orion
orion_threshold_errors: 999
roots_error_threshold: 6
repeat_threshold: 2
llm:
  type: gpt4all
  cmd: gpt4all
github:
  token_env: GITHUB_TOKEN
playwright:
  pages:
    - http://localhost:3000/
    - http://localhost:3000/state-mining
  click_selectors:
    - "button[data-test=initialize]"
    - "button[data-test=submit]"
EOL
    discord_alert "⚠️ Config par défaut créée." "info"
else
    echo -e "${GREEN}✅ Config trouvée: $CFG_PATH${RESET}"
fi

# Créer dossiers persistants
mkdir -p /work/data /work/patches

launch_worker() {
    echo -e "${BLUE}🚀 Lancement du worker Orion via docker-compose...${RESET}"
    if ! docker-compose -f "$DOCKER_COMPOSE_PATH" up -d --build; then
        echo -e "${RED}💥 Erreur lors du build ou lancement du worker!${RESET}"
        discord_alert "💥 Erreur build/lancement worker!" "error"
        github_issue "🚨 Build/Run failure" "Erreur détectée lors du build ou lancement du worker Orion."
    else
        discord_alert "🚀 Orion Worker lancé/relaunch avec succès sur $DISCORD_SERVER_LINK" "success"
    fi
}

live_watch() {
    echo -e "${MAGENTA}🔍 Watch des fichiers src/ et config/...${RESET}"
    command -v inotifywait >/dev/null 2>&1 || {
        echo -e "${YELLOW}⚠️ inotifywait non trouvé. Installer 'inotify-tools' pour live rebuild.${RESET}";
        return;
    }
    while inotifywait -e modify,create,delete -r /work/src /work/config; do
        echo -e "${YELLOW}⚡ Changement détecté ! Rebuild et relaunch...${RESET}"
        discord_alert "⚡ Changement détecté, rebuild en cours..." "info"
        launch_worker
        echo -e "${GREEN}✅ Rebuild et relaunch terminés.${RESET}"
        discord_alert "✅ Rebuild et relaunch terminés." "success"
    done
}

# Lancer watch en arrière-plan
live_watch &

# Boucle chaos: keep worker alive
while true; do
    if ! docker ps | grep -q "$CONTAINER_NAME"; then
        echo -e "${RED}💥 Container crashé ou absent ! Relance en cours...${RESET}"
        discord_alert "💥 Container crashé ou absent ! Relance..." "error"
        launch_worker
        sleep 5
    else
        echo -e "${GREEN}🟢 Container vivant et en ligne.${RESET}"
        sleep 10
    fi
done
