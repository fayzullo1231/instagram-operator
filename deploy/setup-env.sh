#!/usr/bin/env bash
# VNC konsolda paste ishlamasa — har bir qiymatni qo'lda kiritasiz
# Ishlatish: cd /opt/instagram-operator && bash deploy/setup-env.sh
set -euo pipefail

ENV_FILE="${1:-/opt/instagram-operator/.env}"

echo "=== .env sozlash (har satrni Enter bilan tasdiqlang) ==="
echo "Bo'sh qoldirsangiz — standart qiymat ishlatiladi"
echo ""

read -rp "OPENAI_API_KEY: " OPENAI_KEY
read -rp "ZERNIO_API_KEY: " ZERNIO_KEY
read -rp "LINKO_API_TOKEN [Enter=standart]: " LINKO_TOKEN
read -rp "MDOKON_API_KEY [Enter=standart]: " MDOKON_KEY

LINKO_TOKEN="${LINKO_TOKEN:-eca09f333e011e3d1b3b4a722ca11d203a168635}"
MDOKON_KEY="${MDOKON_KEY:-5ddeec9a-a108-11f0-b8d0-0242ac130001}"
ZERNIO_ACCOUNT="${ZERNIO_ACCOUNT_ID:-6a2dd28a5f7d1751aba6f98e}"

cat > "$ENV_FILE" << EOF
# Application
APP_NAME=Instagram AI Operator
APP_ENV=production
LOG_LEVEL=INFO
ALLOWED_HOSTS=13.140.146.78,localhost,127.0.0.1
SYNC_INTERVAL_MINUTES=5
SYNC_ON_STARTUP=true
SYNC_STARTUP_DELAY_SECONDS=10
SCHEDULER_ENABLED=true
DJANGO_SECRET_KEY=KulolOptomServerSecret2026RandomKey

# Server
GUNICORN_BIND=0.0.0.0:8010
GUNICORN_WORKERS=2
PUBLIC_BASE_URL=http://13.140.146.78:8010

# OpenAI
OPENAI_API_KEY=${OPENAI_KEY}
OPENAI_MODEL=gpt-4o

# Linko
LINKO_API_URL=https://kuloloptomuz.linko.uz/ru/api/v1/main/product_list_pos/
LINKO_API_TOKEN=${LINKO_TOKEN}

# MDoKon
MDOKON_API_URL=https://cabinet.mdokon.uz/services/web/api/report-balance-product-api
MDOKON_API_KEY=${MDOKON_KEY}

# TezPOS
TEZPOS_ENABLED=true
TEZPOS_API_URL=http://127.0.0.1:8000
TEZPOS_SERVER_NAME=demo
TEZPOS_LOGIN=demo
TEZPOS_PASSWORD=demo123

# Instagram Zernio
INSTAGRAM_ENABLED=true
ZERNIO_API_KEY=${ZERNIO_KEY}
ZERNIO_API_URL=https://zernio.com/api/v1
ZERNIO_ACCOUNT_ID=${ZERNIO_ACCOUNT}
INSTAGRAM_POLL_INTERVAL_SECONDS=30
INSTAGRAM_MEDIA_AMOUNT=5
INSTAGRAM_CONVERSATION_LIMIT=8
INSTAGRAM_MESSAGE_LIMIT=15
INSTAGRAM_MESSAGE_FETCH_LIMIT=50
INSTAGRAM_COMMENT_POLL_EVERY=3
INSTAGRAM_MAX_MESSAGE_AGE_HOURS=72
ZERNIO_MIN_REQUEST_INTERVAL_SECONDS=1.1

# Qidiruv
FUZZ_MIN_SIMILARITY=60
FUZZ_TOP_N=5
IMAGE_MATCH_MIN_SCORE=75
IMAGE_SEARCH_MIN_FUZZ=85
EOF

chmod 600 "$ENV_FILE"
echo ""
echo "Tayyor: $ENV_FILE"
echo "Keyin: systemctl restart instagram-operator"
