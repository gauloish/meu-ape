#!/bin/bash
# ------------------------------------------------------------------------------
# Script: setup_geocoder.sh
# Objetivo: Baixar, clipar e construir o banco local do Photon para Goiânia.
# ------------------------------------------------------------------------------

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

ARTIFACTS_DIR="$PROJECT_ROOT/artifacts/geocoder"
NOMINATIM_DIR="$ARTIFACTS_DIR/nominatim"
OPEN_STREET_MAP_DIR="$ARTIFACTS_DIR/open_street_map"
PHOTON_DIR="$ARTIFACTS_DIR/photon"

PBF_URL="https://download.geofabrik.de/south-america/brazil/centro-oeste-latest.osm.pbf"
PHOTON_URL="https://github.com/komoot/photon/releases/download/1.2.1/photon-1.2.1.jar"
BBOX="-49.45,-16.85,-49.15,-16.55"
DB_PASS="password"

source "$SCRIPT_DIR/../utils.sh"

# ------------------------------------------------------------------------------

log_info "Iniciando configuração do Geocoder."

log_info "[1/6] Configurando estrutura de diretórios."
mkdir -p "$ARTIFACTS_DIR"
mkdir -p "$NOMINATIM_DIR"
mkdir -p "$OPEN_STREET_MAP_DIR"
mkdir -p "$PHOTON_DIR"
log_info "Artefatos salvos em: $ARTIFACTS_DIR."

log_info "[2/6] Download e clipagem (OSM)." 

if [ ! -f "$OPEN_STREET_MAP_DIR/centro-oeste-latest.osm.pbf" ]; then
    log_info "Baixando dados do Centro-Oeste."
    wget -O "$OPEN_STREET_MAP_DIR/centro-oeste-latest.osm.pbf" "$PBF_URL"
else
    log_info "Dados do Centro-Oeste já encontrados em cache. Pulando download."
fi

if [ ! -f "$NOMINATIM_DIR/goiania.osm.pbf" ]; then
    log_info "Recortando o mapa para o perímetro de Goiânia."
    osmium extract -b "$BBOX" "$OPEN_STREET_MAP_DIR/centro-oeste-latest.osm.pbf" -o "$NOMINATIM_DIR/goiania.osm.pbf"
else
    log_info "Recorte de Goiânia já encontrado em cache."
fi


log_info "[3/6] Inicializando banco temporário (Nominatim)."

if docker ps -a --format '{{.Names}}' | grep -Eq "^nominatim_temp\$"; then
    log_info "Limpando contêiner antigo."
    docker rm -f nominatim_temp > /dev/null
fi

docker run -d --rm \
    -e PBF_PATH=/nominatim/data/goiania.osm.pbf \
    -e NOMINATIM_PASSWORD="$DB_PASS" \
    -v "$NOMINATIM_DIR":/nominatim/data:z \
    -p 5432:5432 \
    --name nominatim_temp \
    mediagis/nominatim:4.4


log_info "[4/6] Aguardando inicialização do PostgreSQL."

until docker exec nominatim_temp pg_isready -U nominatim > /dev/null 2>&1; do
    sleep 5
done

log_info "Banco de dados pronto!"


log_info "[5/6] Extração e geração do índice Photon."

if [ ! -f "$PHOTON_DIR/photon.jar" ]; then
    log_info "Baixando o Photon."
    wget -O "$PHOTON_DIR/photon.jar" "$PHOTON_URL"
fi

cd "$PHOTON_DIR"

if [ -d "$PHOTON_DIR/photon_data" ]; then
    log_info "Removendo banco Photon antigo."
    rm -rf "$PHOTON_DIR/photon_data"
fi

log_info "Importando dados do Nominatim para o Photon."
java -jar "$PHOTON_DIR/photon.jar" import -host 127.0.0.1 -port 5432 -database nominatim -user nominatim -password "$DB_PASS"


log_info "[6/6] Limpeza (Teardown)."
docker stop nominatim_temp

log_success "Setup Conluído."