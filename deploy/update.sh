#!/usr/bin/env bash
# Serverda yangilash: bash deploy/update.sh
set -euo pipefail

APP_DIR="/opt/instagram-operator"
cd "$APP_DIR"

echo "=== Git pull ==="
git pull origin main

echo "=== Dependencies ==="
venv/bin/pip install -r requirements.txt -q

echo "=== Migrate ==="
venv/bin/python manage.py migrate --noinput
venv/bin/python manage.py collectstatic --noinput 2>/dev/null || true

echo "=== Restart ==="
sudo systemctl restart instagram-operator
sudo systemctl status instagram-operator --no-pager

echo "=== Tayyor ==="
