#!/bin/bash
# ------------------------------------------------------------------------------
# Script: utils.sh
# Objetivo: Funções utilitárias e padronização de logs com cores.
# ------------------------------------------------------------------------------

readonly COLOR_BOLD='\033[1m'       # Bold
readonly COLOR_INFO='\033[0;36m'    # Ciano
readonly COLOR_SUCCESS='\033[0;32m' # Verde
readonly COLOR_WARN='\033[1;33m'    # Amarelo
readonly COLOR_ERROR='\033[0;31m'   # Vermelho
readonly COLOR_RESET='\033[0m'      # Remove a formatação

_timestamp() {
    date +"%Y-%m-%d %H:%M:%S"
}

log_info() {
    echo -e "${COLOR_BOLD}[$(_timestamp)]${COLOR_RESET} ${COLOR_INFO}INFO${COLOR_RESET}: $1"
}

log_success() {
    echo -e "${COLOR_BOLD}[$(_timestamp)]${COLOR_RESET} ${COLOR_SUCCESS}SUCCESS${COLOR_RESET}: $1"
}

log_warn() {
    echo -e "${COLOR_BOLD}[$(_timestamp)]${COLOR_RESET} ${COLOR_WARN}WARN${COLOR_RESET}: $1"
}

log_error() {
    echo -e "${COLOR_BOLD}[$(_timestamp)]${COLOR_RESET} ${COLOR_ERROR}ERROR${COLOR_RESET}: $1" >&2
}