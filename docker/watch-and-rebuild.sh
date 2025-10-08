#!/bin/bash

cd "$(dirname "$0")"

COMPOSE_FILE="docker-compose.slim.yml"
SERVICE_NAME="orion-worker"
WATCH_DIRS="../src ../scripts ../config"

echo "🦅 Watcher activé sur : $WATCH_DIRS"
echo "Ctrl+C pour quitter"

# Fonction de build et run
build_and_run() {
    echo "💀 Nettoyage des containers obsolètes..."
    docker-compose -f $COMPOSE_FILE down --remove-orphans
    docker image prune -f -q

    echo "⚡ Build de l'image Docker slim..."
    docker-compose -f $COMPOSE_FILE build --no-cache

    echo "🚀 Démarrage du worker Orion..."
    docker-compose -f $COMPOSE_FILE up -d

    echo "✅ Worker démarré."
}

# Build initial
build_and_run

# Surveille les changements avec inotifywait
while true; do
    inotifywait -e modify,create,delete -r $WATCH_DIRS
    echo "🔁 Changement détecté, rebuild..."
    build_and_run
done
