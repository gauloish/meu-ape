#!/bin/bash
# ------------------------------------------------------------------------------
# Script: start_geocoder.sh
# Objetivo: Iniciar a API local do Photon para geocodificação.
# ------------------------------------------------------------------------------

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

ARTIFACTS_DIR="$PROJECT_ROOT/artifacts/geocoder"
PHOTON_DIR="$ARTIFACTS_DIR/photon"
DB_DIR="$PHOTON_DIR"
JAR_FILE="$PHOTON_DIR/photon.jar"

source "$SCRIPT_DIR/../utils.sh"

# ------------------------------------------------------------------------------

log_info "Iniciando atualização do Geocoder."

log_info "[1/3] Checando executável do Photon."

if [ ! -f "$JAR_FILE" ]; then
    log_error "Executável do Photon não encontrado em: $JAR_FILE."
    log_info "Execute 'bash scripts/setup_geocoder.sh' primeiro."
    exit 1
fi

log_info "[2/3] Checando banco de dados do mapa do Photon."

if [ ! -d "$DB_DIR" ]; then
    log_error "Banco de dados do mapa não encontrado em: $DB_DIR."
    log_info "Execute 'bash scripts/setup_geocoder.sh' primeiro."
    exit 1
fi

log_info "[3/3] Iniciando o servidor de Geocodificação (Photon)."

exec java -jar "$JAR_FILE" -data-dir "$DB_DIR" serve

log_sucess "API disponível em: http://localhost:2322/api."