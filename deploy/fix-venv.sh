#!/usr/bin/env bash
# Serverda pip/venv xatosi bo'lsa
# Ishlatish: bash deploy/fix-venv.sh
set -euo pipefail

APP_DIR="/opt/instagram-operator"
cd "$APP_DIR"

git config --global --add safe.directory "$APP_DIR" 2>/dev/null || true

systemctl stop instagram-operator 2>/dev/null || true

apt-get update -qq
apt-get install -y -qq python3 python3-venv python3-pip build-essential git curl
apt-get install -y -qq python3.14-venv 2>/dev/null || true

PYTHON_BIN="python3"
echo "Python: $($PYTHON_BIN --version)"

create_venv() {
  rm -rf venv
  if "$PYTHON_BIN" -m venv venv; then
    return 0
  fi
  echo "ensurepip xato — get-pip.py bilan davom etiladi..."
  "$PYTHON_BIN" -m venv venv --without-pip
  curl -fsSL https://bootstrap.pypa.io/get-pip.py -o /tmp/get-pip.py
  venv/bin/python /tmp/get-pip.py
  rm -f /tmp/get-pip.py
}

create_venv
venv/bin/pip install --upgrade pip
venv/bin/pip install -r requirements.txt

mkdir -p data
SCHEDULER_ENABLED=false venv/bin/python manage.py migrate --noinput
venv/bin/python manage.py collectstatic --noinput 2>/dev/null || true

id instagram &>/dev/null && chown -R instagram:instagram "$APP_DIR" || true
chmod 600 .env 2>/dev/null || true

if [[ -f /etc/systemd/system/instagram-operator.service ]]; then
  systemctl daemon-reload
  systemctl start instagram-operator
  sleep 2
  systemctl status instagram-operator --no-pager
else
  echo "systemd yo'q — qo'lda ishga tushiring:"
  echo "  venv/bin/gunicorn config.wsgi:application --bind 0.0.0.0:8010 --workers 2"
fi

echo "Tayyor. Tekshirish: curl http://127.0.0.1:8010/health"
