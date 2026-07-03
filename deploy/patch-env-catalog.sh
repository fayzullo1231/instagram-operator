#!/usr/bin/env bash
# Mavjud .env ga KulolOptom va MDoKon qatorlarini qo'shish
set -euo pipefail

ENV_FILE="${1:-/opt/instagram-operator/.env}"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Xato: $ENV_FILE topilmadi"
  exit 1
fi

if ! grep -q '^KULOLOPTOM_ENABLED=' "$ENV_FILE"; then
  cat >> "$ENV_FILE" << 'EOF'

# KulolOptom katalog (TezPOS tenant)
KULOLOPTOM_ENABLED=true
KULOLOPTOM_SERVER_NAME=kuloloptom-2
KULOLOPTOM_API_TOKEN=
KULOLOPTOM_LOGIN=
KULOLOPTOM_PASSWORD=
EOF
  echo "KulolOptom qatorlari qo'shildi"
else
  echo "KulolOptom allaqachon mavjud"
fi

if ! grep -q '^MDOKON_API_KEY=' "$ENV_FILE"; then
  cat >> "$ENV_FILE" << 'EOF'

MDOKON_API_URL=https://cabinet.mdokon.uz/services/web/api/report-balance-product-api
MDOKON_API_KEY=5ddeec9a-a108-11f0-b8d0-0242ac130001
EOF
  echo "MDoKon qatorlari qo'shildi"
fi

echo ""
echo "Keyin .env da to'ldiring:"
echo "  KULOLOPTOM_API_TOKEN=... (tavsiya etiladi)"
echo "  yoki KULOLOPTOM_LOGIN=... va KULOLOPTOM_PASSWORD=..."
echo ""
echo "Tekshirish: venv/bin/python manage.py check_product_sync --sync"
