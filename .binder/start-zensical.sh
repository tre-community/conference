#!/usr/bin/env bash
set -euo pipefail

PORT="${1:-8000}"
PREFIX="${2:-/zensical/}"

if [ -n "${JUPYTERHUB_SERVICE_PREFIX:-}" ]; then
  # Inject the Binder session prefix into zensical.toml
  sed -i.bak -E "s|site_url\s*=\s*\".*\"|site_url = \"${JUPYTERHUB_SERVICE_PREFIX}zensical/\"|" zensical.toml
fi

# If running inside JupyterHub/Binder, JUPYTERHUB_SERVICE_PREFIX is available
if [ -n "${JUPYTERHUB_SERVICE_PREFIX:-}" ]; then
  FULL_PREFIX="${JUPYTERHUB_SERVICE_PREFIX}zensical/"
else
  FULL_PREFIX="${PREFIX}"
fi

echo "Starting Zensical preview on port ${PORT} with prefix ${FULL_PREFIX}..."

# Export prefix for any templates or plugins that consume environment variables
export ZENSICAL_BASE_URL="${FULL_PREFIX}"

# Execute Zensical binding to localhost on the assigned proxy port
exec zensical serve --dev-addr "127.0.0.1:${PORT}"
