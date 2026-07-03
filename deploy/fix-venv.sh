#!/usr/bin/env bash
# Serverda pip/venv xatosi bo'lsa
# Ishlatish: bash deploy/fix-venv.sh
set -euo pipefail

APP_DIR="/opt/instagram-operator"
cd "$APP_DIR"

git config --global --add safe.directory "$APP_DIR" 2>/dev/null || true

apt-get update -qq
apt-get install -y -qq python3 python3-venv build-essential git

PYTHON_BIN="python3"
echo "Python: $($PYTHON_BIN --version)"

rm -rf venv
"$PYTHON_BIN" -m venv venv
venv/bin/pip install --upgrade pip
venv/bin/pip install -r requirements.txt

mkdir -p data
venv/bin/python manage.py migrate --noinput
venv/bin/python manage.py collectstatic --noinput 2>/dev/null || true

id instagram &>/dev/null && chown -R instagram:instagram "$APP_DIR" || true
chmod 600 .env 2>/dev/null || true

if [[ -f /etc/systemd/system/instagram-operator.service ]]; then
  systemctl daemon-reload
  systemctl restart instagram-operator
  sleep 2
  systemctl status instagram-operator --no-pager
else
  echo "systemd yo'q — qo'lda ishga tushiring:"
  echo "  venv/bin/gunicorn config.wsgi:application --bind 0.0.0.0:8010 --workers 2"
fi

echo "Tayyor. Tekshirish: curl http://127.0.0.1:8010/health"
