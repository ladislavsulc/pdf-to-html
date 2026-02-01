#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="/home/clawdbot/clawd/pdf-to-html-fork"
SERVICE_NAME="pdf-to-html"
HEALTH_URL="http://127.0.0.1:7860/"

echo "==> Deploying PDF-to-HTML from ${REPO_DIR}"
cd "${REPO_DIR}"

echo "==> Syncing latest main from origin"
git fetch origin
git checkout main
git pull --ff-only origin main

echo "==> Quick syntax check"
python3 -m py_compile gradio_app.py

echo "==> Restarting ${SERVICE_NAME}"
sudo systemctl restart "${SERVICE_NAME}"

echo "==> Waiting for service to become ready"
for _ in $(seq 1 20); do
  if curl -fsS -o /dev/null "${HEALTH_URL}"; then
    echo "==> Deploy successful: ${HEALTH_URL} is reachable"
    exit 0
  fi
  sleep 1
done

echo "ERROR: service did not become healthy in time" >&2
sudo systemctl status "${SERVICE_NAME}" --no-pager || true
exit 1
