#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

cd "$ROOT_DIR"

ACTION="${1:-up}"
MODE="${2:-minimal}"
COMPOSE_FILE="docker-compose.otel-grafana.yml"

profiles=()
case "$MODE" in
  minimal)
    profiles=()
    ;;
  ui)
    profiles+=(--profile ui)
    ;;
  full)
    profiles+=(--profile ui --profile metrics)
    ;;
  *)
    echo "Unknown mode: $MODE"
    echo "Usage: ./run_otel_stack.sh [up|down|ps] [minimal|ui|full]"
    exit 1
    ;;
esac

compose_cmd=(docker compose -f "$COMPOSE_FILE")
if [[ ${#profiles[@]} -gt 0 ]]; then
  compose_cmd+=("${profiles[@]}")
fi

case "$ACTION" in
  up)
    "${compose_cmd[@]}" up -d
    echo "OTel stack is starting in mode: $MODE"
    echo "Tempo:      http://127.0.0.1:3200"
    echo "OTLP HTTP:  http://127.0.0.1:4318"
    if [[ "$MODE" == "ui" || "$MODE" == "full" ]]; then
      echo "Grafana:    http://127.0.0.1:3000 (admin/admin)"
    fi
    if [[ "$MODE" == "full" ]]; then
      echo "Prometheus: http://127.0.0.1:9090"
    fi
    ;;
  down)
    "${compose_cmd[@]}" down
    ;;
  ps)
    "${compose_cmd[@]}" ps
    ;;
  *)
    echo "Unknown action: $ACTION"
    echo "Usage: ./run_otel_stack.sh [up|down|ps] [minimal|ui|full]"
    exit 1
    ;;
esac
