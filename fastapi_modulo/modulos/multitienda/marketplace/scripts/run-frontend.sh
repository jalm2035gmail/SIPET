#!/usr/bin/env bash
set -euo pipefail

# Navega al frontend público y ejecuta npm install + dev para levantar la app.
cd "$(dirname "${BASH_SOURCE[0]}")/../frontend/public"
npm install
npm run dev
