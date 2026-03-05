#!/usr/bin/env bash
set -euo pipefail

# Alias explicito para despliegue de Polotitlan.
# Mantiene la misma logica de deploy-sipet.sh para evitar divergencias.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "${SCRIPT_DIR}/deploy-sipet.sh" "$@"
