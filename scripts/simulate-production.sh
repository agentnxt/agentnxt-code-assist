#!/usr/bin/env bash
set -euo pipefail

ACTION="${1:-up}"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET_DIR="$ROOT_DIR/tmp/simulation-target"
COMPOSE=(docker compose -f docker-compose.yml -f docker-compose.simulation.yml)
PROJECT_NAME="${COMPOSE_PROJECT_NAME:-agennext-code-assist-sim}"
API_PORT="${AGENNEXT_CODE_ASSIST_PORT:-8090}"
WEB_PORT="${AGENNEXT_CODE_ASSIST_WEB_PORT:-3000}"
API_URL="http://localhost:${API_PORT}"
WEB_URL="http://localhost:${WEB_PORT}"

export COMPOSE_PROJECT_NAME="$PROJECT_NAME"
export AGENNEXT_CODE_ASSIST_PORT="$API_PORT"
export AGENNEXT_CODE_ASSIST_WEB_PORT="$WEB_PORT"
export NEXT_PUBLIC_AGENNEXT_CODE_ASSIST_API_URL="$API_URL"

log() {
  printf '\n==> %s\n' "$*"
}

require_docker() {
  if ! command -v docker >/dev/null 2>&1; then
    echo "Docker CLI was not found. Install Docker Desktop first." >&2
    exit 1
  fi
  if ! docker info >/dev/null 2>&1; then
    echo "Docker is not running. Start Docker Desktop and retry." >&2
    exit 1
  fi
}

wait_for_url() {
  local url="$1"
  local name="$2"
  local attempts="${3:-60}"
  for _ in $(seq 1 "$attempts"); do
    if curl -fsS "$url" >/dev/null 2>&1; then
      echo "$name is ready: $url"
      return 0
    fi
    sleep 2
  done
  echo "$name did not become ready: $url" >&2
  return 1
}

prepare_target_repo() {
  log "Preparing local simulation target repository"
  rm -rf "$TARGET_DIR"
  mkdir -p "$TARGET_DIR/src" "$TARGET_DIR/tests"
  cat > "$TARGET_DIR/README.md" <<'README'
# Simulation Target

This repo is used by AGenNext Code Assist Docker Desktop production simulation.

## Commands

```bash
npm run type-check
npm run lint
npm run test
npm run build
```
README
  cat > "$TARGET_DIR/package.json" <<'JSON'
{
  "name": "agennext-code-assist-simulation-target",
  "version": "0.1.0",
  "private": true,
  "scripts": {
    "type-check": "node -e \"console.log('type-check ok')\"",
    "lint": "node -e \"console.log('lint ok')\"",
    "test": "node -e \"console.log('unit ok')\"",
    "build": "node -e \"console.log('build ok')\"",
    "smoke": "node -e \"console.log('smoke ok')\""
  },
  "dependencies": {}
}
JSON
  cat > "$TARGET_DIR/src/index.js" <<'JS'
function hello(name) {
  return `hello ${name}`;
}

module.exports = { hello };
JS
  cat > "$TARGET_DIR/tests/index.test.js" <<'JS'
const { hello } = require('../src');
if (hello('agennext') !== 'hello agennext') {
  throw new Error('unexpected greeting');
}
JS
  cat > "$TARGET_DIR/Dockerfile" <<'DOCKER'
FROM node:20-alpine
WORKDIR /app
COPY package.json ./
COPY src ./src
CMD ["node", "src/index.js"]
DOCKER
  (cd "$TARGET_DIR" && git init >/dev/null && git config user.email "simulation@agennext.local" && git config user.name "AGenNext Simulation" && git add . && git commit -m "Initial simulation target" >/dev/null)
}

run_e2e_smoke() {
  log "Running end-to-end backend smoke request"
  local payload
  payload=$(cat <<JSON
{
  "instruction": "Dry run only. Inspect this simulation target and report production readiness. Do not modify files.",
  "repo_path": "/simulation-target",
  "files": ["README.md", "package.json", "src/index.js"],
  "checks": ["typecheck", "lint", "unit", "smoke"],
  "dry_run": true,
  "write_change_log": false,
  "audit_repo": true,
  "audit_dependencies": true,
  "notify_slack": false,
  "notify_webhook": false,
  "notify_smtp": false
}
JSON
)
  curl -fsS -X POST "$API_URL/assist" \
    -H "Content-Type: application/json" \
    -d "$payload" \
    -o "$ROOT_DIR/tmp/simulation-result.json"
  echo "E2E result written to tmp/simulation-result.json"
}

up() {
  require_docker
  prepare_target_repo
  log "Building and starting backend + Next.js web UI in Docker Desktop"
  "${COMPOSE[@]}" --profile simulation --profile web up -d --build agennext-code-assist agennext-code-assist-web
  wait_for_url "$API_URL/healthz" "AGenNext Code Assist API"
  wait_for_url "$WEB_URL" "AGenNext Code Assist Web UI"
  run_e2e_smoke
  log "Simulation environment is running"
  echo "API: $API_URL"
  echo "Web UI: $WEB_URL"
  echo "Stop with: scripts/simulate-production.sh down"
}

up_full() {
  require_docker
  prepare_target_repo
  log "Building and starting backend + web + edge + optional ops stack"
  "${COMPOSE[@]}" --profile simulation --profile web --profile simulation-edge --profile ops up -d --build
  wait_for_url "$API_URL/healthz" "AGenNext Code Assist API"
  wait_for_url "$WEB_URL" "AGenNext Code Assist Web UI"
  run_e2e_smoke
  log "Full simulation environment is running"
  echo "API: $API_URL"
  echo "Web UI: $WEB_URL"
  echo "Uptime Kuma: http://localhost:${UPTIME_KUMA_PORT:-3001}"
  echo "Healthchecks: http://localhost:${HEALTHCHECKS_PORT:-8000}"
  echo "GlitchTip: http://localhost:${GLITCHTIP_PORT:-8081}"
  echo "SigNoz: http://localhost:${SIGNOZ_PORT:-3301}"
  echo "Infisical: http://localhost:${INFISICAL_PORT:-8082}"
  echo "Caddy HTTP: http://localhost:${CADDY_HTTP_PORT:-8088}"
  echo "Caddy HTTPS: https://localhost:${CADDY_HTTPS_PORT:-8443}"
  echo "Stop with: scripts/simulate-production.sh down"
}

down() {
  require_docker
  log "Stopping simulation environment"
  "${COMPOSE[@]}" --profile simulation --profile web --profile simulation-edge --profile ops down
}

clean() {
  require_docker
  log "Removing simulation environment and volumes"
  "${COMPOSE[@]}" --profile simulation --profile web --profile simulation-edge --profile ops down -v --remove-orphans
  rm -rf "$ROOT_DIR/tmp/simulation-target" "$ROOT_DIR/tmp/simulation-result.json"
}

case "$ACTION" in
  up) up ;;
  full) up_full ;;
  down) down ;;
  clean) clean ;;
  *)
    echo "Usage: $0 [up|full|down|clean]" >&2
    exit 2
    ;;
esac
