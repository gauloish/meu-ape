#!/bin/bash
# ------------------------------------------------------------------------------
# Script: start.sh
# Objetivo: Iniciar a API local do Photon para geocodificação.
# ------------------------------------------------------------------------------

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

ARTIFACTS_DIR="$PROJECT_ROOT/artifacts/geocoder"
NOMINATIM_DIR="$ARTIFACTS_DIR/nominatim"
OSM_FILE="$NOMINATIM_DIR/goiania.osm.pbf"

source "$SCRIPT_DIR/../utils.sh"

# ------------------------------------------------------------------------------

log_info "Iniciando atualização do Geocoder (Nomantim)."


log_info "[1/4] Checando pasta do Nominatim."

if [ ! -d "$NOMINATIM_DIR" ]; then
    log_error "Pasta do Nominatim não encontrada em: $NOMINATIM_DIR."
    log_info "Execute 'bash scripts/setup_geocoder.sh' primeiro."
    exit 1
fi


log_info "[2/4] Checando o arquivo do mapa de Goiânia."

if [ ! -f "$OSM_FILE" ]; then
    log_error "Arquivo do mapa de Goiânia não encontrado em: $OSM_FILE."
    log_info "Execute 'bash scripts/setup_geocoder.sh' primeiro."
    exit 1
fi


log_info "[3/4] Limpando o contêiner do antigo servidor Nomantim."

if docker ps -a --format '{{.Names}}' | grep -Eq "^nominatim\$"; then
    log_info "Limpando contêiner antigo."
    docker rm -f nominatim > /dev/null
fi


log_info "[4/4] Iniciando o servidor de Geocodificação (Nominatim)."

docker run -it --shm-size=1g \
    -e PBF_PATH=/nominatim/data/goiania.osm.pbf \
    -e NOMINATIM_PASSWORD=password\
    -v "$NOMINATIM_DIR":/nominatim/data:Z \
    -v nominatim-data:/var/lib/postgresql/16/main \
    -p 8080:8080 \
    --name nominatim \
    mediagis/nominatim:5.3

log_sucess "API disponível em: http://localhost:2322/api."