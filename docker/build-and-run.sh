#!/bin/bash

cd "$(dirname "$0")"

COMPOSE_FILE="docker-compose.slim.yml"
SERVICE_NAME="orion-worker"

echo "💀 Nettoyage des containers et images obsolètes..."
docker-compose -f $COMPOSE_FILE down --remove-orphans
docker image prune -f

echo "⚡ Build de l'image Docker slim..."
docker-compose -f $COMPOSE_FILE build --no-cache

echo "🚀 Démarrage du worker Orion..."
docker-compose -f $COMPOSE_FILE up -d

echo "📖 Suivi des logs en temps réel (Ctrl+C pour quitter)..."
docker-compose -f $COMPOSE_FILE logs -f $SERVICE_NAME
