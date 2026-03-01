#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

export ADK_SESSION_SERVICE_URI="${ADK_SESSION_SERVICE_URI:-postgresql+psycopg://adk:adk@127.0.0.1:5432/adk}"

cd "${ROOT_DIR}/agents"
poetry run adk web --session_service_uri="${ADK_SESSION_SERVICE_URI}" .
