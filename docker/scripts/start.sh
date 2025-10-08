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

CONTAINER_NAME="docker-orion-worker-1"
# shellcheck disable=SC2034
IMAGE_NAME="docker-orion-worker"
DOCKER_COMPOSE_PATH="/work/docker/docker-compose.yml"

# Discord setup
# shellcheck disable=SC2034
DISCORD_CHANNEL_ID="1425382514322833489"
DISCORD_SERVER_LINK="https://discord.gg/Dt7zvuFPGf"
DISCORD_WEBHOOK=$(grep discord_webhook /work/config/worker_config.yml | awk '{print $2}')

timestamp() {
    date +"%Y-%m-%d %H:%M:%S"
}

discord_alert() {
    local MESSAGE="$1"
    local TYPE="${2:-info}" # info / error / success
    if [[ -n "$DISCORD_WEBHOOK" ]]; then
        curl -s -H "Content-Type: application/json" \
             -X POST \
             -d "{\"content\":\"[$(timestamp)] [$TYPE] $MESSAGE\"}" \
             "$DISCORD_WEBHOOK" >/dev/null 2>&1 || true
    fi
}

echo -e "${CYAN}🦅 Orion Chaos Live Rebuild + AI Monitoring activé...${RESET}"

# Vérifier config
if [[ ! -f "${CFG_PATH}" ]]; then
    echo -e "${RED}❌ Config introuvable: ${CFG_PATH}${RESET}"
    discord_alert "❌ Config introuvable à ${CFG_PATH}" "error"
    exit 1
else
    echo -e "${GREEN}✅ Config trouvée: ${CFG_PATH}${RESET}"
fi

mkdir -p "$(dirname "${DB_PATH}")"
mkdir -p "${PATCH_DIR}"

launch_worker() {
    echo -e "${BLUE}🚀 Lancement du worker Orion via docker-compose...${RESET}"
    docker-compose -f $DOCKER_COMPOSE_PATH up -d --build
    discord_alert "🚀 Orion Worker lancé ou relancé avec succès sur $DISCORD_SERVER_LINK" "success"
}

live_watch() {
    echo -e "${MAGENTA}🔍 Watch des fichiers src/ et config/...${RESET}"
    if ! command -v inotifywait >/dev/null 2>&1; then
        echo -e "${YELLOW}⚠️ inotifywait non trouvé, installer 'inotify-tools' pour live rebuild.${RESET}"
        return
    fi

    while inotifywait -e modify,create,delete -r /work/src /work/config; do
        echo -e "${YELLOW}⚡ Changement détecté ! Rebuild et relaunch...${RESET}"
        discord_alert "⚡ Changement détecté dans src/ ou config/, rebuild en cours..." "info"
        docker-compose -f $DOCKER_COMPOSE_PATH up -d --build
        echo -e "${GREEN}✅ Rebuild et relaunch terminés.${RESET}"
        discord_alert "✅ Rebuild et relaunch terminés." "success"
    done
}

# Watch en arrière-plan
live_watch &

# Boucle chaos: keep worker alive
while true; do
    if ! docker ps | grep -q $CONTAINER_NAME; then
        echo -e "${RED}💥 Container crashé ou absent ! Relance en cours...${RESET}"
        discord_alert "💥 Container crashé ou absent ! Relance en cours..." "error"
        launch_worker
        sleep 5
    else
        echo -e "${GREEN}🟢 Container vivant et en ligne.${RESET}"
        sleep 10
    fi
done
# ... avant reste pareil ...

# Fonction GitHub issue intelligente
create_github_issue_if_critical() {
    local TITLE="$1"
    local BODY="$2"
    local SEVERITY="$3"  # critical / needs-fix

    # Ne poster que si token dispo
    if [[ -n "$GITHUB_TOKEN" ]]; then
        # Exclusion: vérifier si issue similaire existe déjà
        EXISTING=$(curl -s -H "Authorization: token $GITHUB_TOKEN" \
            -H "Accept: application/vnd.github+json" \
            "https://api.github.com/repos/$GITHUB_REPO_OWNER/$GITHUB_REPO_NAME/issues?state=open" \
            | grep -F "$TITLE" || true)

        if [[ -z "$EXISTING" ]]; then
            curl -s -H "Authorization: token $GITHUB_TOKEN" \
                 -H "Accept: application/vnd.github+json" \
                 "https://api.github.com/repos/$GITHUB_REPO_OWNER/$GITHUB_REPO_NAME/issues" \
                 -d "{\"title\":\"$TITLE\",\"body\":\"$BODY\",\"labels\":[\"$SEVERITY\"]}" >/dev/null 2>&1 || true
        fi
    fi
}

# Boucle chaos: keep worker alive
while true; do
    if ! docker ps | grep -q $CONTAINER_NAME; then
        echo -e "${RED}💥 Container crashé ou absent ! Relance en cours...${RESET}"
        discord_alert "💥 Container crashé ou absent ! Relance en cours..." "error"

        # GitHub only si crash bloquant
        create_github_issue_if_critical "Crash Orion Worker" "Le container $CONTAINER_NAME est mort à $(timestamp)." "critical"

        launch_worker
        sleep 5
    else
        echo -e "${GREEN}🟢 Container vivant et en ligne.${RESET}"
        sleep 10
    fi
done
