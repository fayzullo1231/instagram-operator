#!/usr/bin/env bash
# KulolOptom tokenini .env ga qo'shish
# Ishlatish: bash deploy/set-kuloloptom-token.sh YOUR_TOKEN
set -euo pipefail

TOKEN="${1:-}"
ENV_FILE="${2:-/opt/instagram-operator/.env}"

if [[ -z "$TOKEN" ]]; then
  echo "Ishlatish: bash deploy/set-kuloloptom-token.sh TOKEN"
  exit 1
fi

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Xato: $ENV_FILE topilmadi"
  exit 1
fi

bash "$(dirname "$0")/patch-env-catalog.sh" "$ENV_FILE"

python3 - "$ENV_FILE" "$TOKEN" <<'PY'
import re
import sys
from pathlib import Path

env_path = Path(sys.argv[1])
token = sys.argv[2].strip()
text = env_path.read_text(encoding="utf-8")

def set_var(name: str, value: str) -> None:
    global text
    pattern = rf"^{re.escape(name)}=.*$"
    line = f"{name}={value}"
    if re.search(pattern, text, flags=re.M):
        text = re.sub(pattern, line, text, count=1, flags=re.M)
    else:
        text = text.rstrip() + "\n" + line + "\n"

set_var("KULOLOPTOM_ENABLED", "true")
set_var("KULOLOPTOM_SERVER_NAME", "kuloloptom-2")
set_var("KULOLOPTOM_API_TOKEN", token)
set_var("KULOLOPTOM_LOGIN", "")
set_var("KULOLOPTOM_PASSWORD", "")
set_var("TEZPOS_API_URL", "http://127.0.0.1:8000")

env_path.write_text(text, encoding="utf-8")
print(f"Yangilandi: {env_path}")
PY

echo ""
echo "Keyin:"
echo "  cd /opt/instagram-operator"
echo "  git pull"
echo "  sudo systemctl restart instagram-operator"
echo "  venv/bin/python manage.py check_product_sync --sync"
