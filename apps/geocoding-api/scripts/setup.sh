#!/bin/bash
# ------------------------------------------------------------------------------
# Script: setup.sh
# Objetivo: Baixar, clipar e construir o banco local do Nominatim para Goiânia.
# ------------------------------------------------------------------------------

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

ARTIFACTS_DIR="$PROJECT_ROOT/artifacts/geocoder"
NOMINATIM_DIR="$ARTIFACTS_DIR/nominatim"
OPEN_STREET_MAP_DIR="$ARTIFACTS_DIR/open_street_map"

PBF_URL="https://download.geofabrik.de/south-america/brazil/centro-oeste-latest.osm.pbf"
BBOX="-49.45,-16.85,-49.15,-16.55"

source "$SCRIPT_DIR/../utils.sh"

# ------------------------------------------------------------------------------

log_info "Iniciando configuração do Geocoder."

log_info "[1/3] Configurando estrutura de diretórios."
mkdir -p "$ARTIFACTS_DIR"
mkdir -p "$NOMINATIM_DIR"
mkdir -p "$OPEN_STREET_MAP_DIR"
log_info "Artefatos salvos em: $ARTIFACTS_DIR."

log_info "[2/3] Download do mapa do Centro-Oeste (OSM)."

if [ ! -f "$OPEN_STREET_MAP_DIR/centro-oeste-latest.osm.pbf" ]; then
    log_info "Baixando dados do Centro-Oeste."
    wget -O "$OPEN_STREET_MAP_DIR/centro-oeste-latest.osm.pbf" "$PBF_URL"
else
    log_info "Dados do Centro-Oeste já encontrados em cache. Pulando download."
fi

log_info "[3/3] Clipagem de Goiânia no mapa do Centro-Oeste (OSM)."

if [ ! -f "$NOMINATIM_DIR/goiania.osm.pbf" ]; then
    log_info "Recortando o mapa para o perímetro de Goiânia."
    osmium extract -b "$BBOX" "$OPEN_STREET_MAP_DIR/centro-oeste-latest.osm.pbf" -o "$NOMINATIM_DIR/goiania.osm.pbf"
else
    log_info "Recorte de Goiânia já encontrado em cache."
fi

log_success "Setup Conluído."