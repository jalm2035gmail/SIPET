#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PYTHON_BIN="${ROOT_DIR}/backend/venv/bin/python"
MANAGE_PY="${ROOT_DIR}/backend/django_project/manage.py"
LOG_DIR="${ROOT_DIR}/.run"
LOG_FILE="${LOG_DIR}/segmentacion_diaria.log"

mkdir -p "${LOG_DIR}"

if [[ ! -x "${PYTHON_BIN}" ]]; then
  echo "Python virtualenv no encontrado en ${PYTHON_BIN}" | tee -a "${LOG_FILE}"
  exit 1
fi

{
  echo "=== $(date '+%Y-%m-%d %H:%M:%S') segmentacion_socios ==="
  "${PYTHON_BIN}" "${MANAGE_PY}" segmentar_socios --engine auto
  echo ""
} >>"${LOG_FILE}" 2>&1
