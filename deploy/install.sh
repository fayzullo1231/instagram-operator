#!/usr/bin/env bash
# Birinchi marta Contabo serverda o'rnatish
# Ishlatish: sudo bash deploy/install.sh
set -euo pipefail

APP_DIR="/opt/instagram-operator"
APP_USER="instagram"
REPO_URL="${REPO_URL:-https://github.com/fayzullo1231/instagram-operator.git}"
BRANCH="${BRANCH:-main}"

echo "=== Instagram AI Operator — o'rnatish ==="

if [[ $EUID -ne 0 ]]; then
  echo "sudo bilan ishga tushiring: sudo bash deploy/install.sh"
  exit 1
fi

apt-get update -qq
apt-get install -y -qq python3.12 python3.12-venv python3-pip git build-essential

PYTHON_BIN="python3.12"
if ! command -v "$PYTHON_BIN" &>/dev/null; then
  PYTHON_BIN="python3"
fi

id "$APP_USER" &>/dev/null || useradd --system --home-dir "$APP_DIR" --shell /usr/sbin/nologin "$APP_USER"

mkdir -p "$APP_DIR"
chown "$APP_USER:$APP_USER" "$APP_DIR"

if [[ ! -d "$APP_DIR/.git" ]]; then
  sudo -u "$APP_USER" git clone -b "$BRANCH" "$REPO_URL" "$APP_DIR"
else
  echo "Repo mavjud: $APP_DIR"
fi

cd "$APP_DIR"

if [[ ! -f .env ]]; then
  cp .env.example .env
  echo ""
  echo "DIQQAT: .env faylini to'ldiring: nano $APP_DIR/.env"
fi

sudo -u "$APP_USER" "$PYTHON_BIN" -m venv venv
sudo -u "$APP_USER" venv/bin/pip install --upgrade pip -q
sudo -u "$APP_USER" venv/bin/pip install -r requirements.txt -q
sudo -u "$APP_USER" mkdir -p data
sudo -u "$APP_USER" venv/bin/python manage.py migrate --noinput
sudo -u "$APP_USER" venv/bin/python manage.py collectstatic --noinput 2>/dev/null || true

cp deploy/instagram-operator.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable instagram-operator
systemctl restart instagram-operator

echo ""
echo "=== Tayyor ==="
echo "Panel:    http://$(curl -s ifconfig.me 2>/dev/null || echo SERVER_IP):8010/panel/"
echo "Health:   http://$(curl -s ifconfig.me 2>/dev/null || echo SERVER_IP):8010/health"
echo "Holat:    systemctl status instagram-operator"
echo ""
echo "Admin:    cd $APP_DIR && sudo -u $APP_USER venv/bin/python manage.py createsuperuser"
