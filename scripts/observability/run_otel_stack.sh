#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

cd "$ROOT_DIR"

docker compose -f docker-compose.otel-grafana.yml up -d

echo "OTel stack is starting..."
echo "Grafana:    http://127.0.0.1:3000 (admin/admin)"
echo "Prometheus: http://127.0.0.1:9090"
echo "Tempo:      http://127.0.0.1:3200"
echo "OTLP HTTP:  http://127.0.0.1:4318"
