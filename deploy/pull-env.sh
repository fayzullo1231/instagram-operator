#!/usr/bin/env bash
# .env ni gitdan olish (private repo)
# Ishlatish: bash deploy/pull-env.sh
set -euo pipefail
cd /opt/instagram-operator
git pull origin main
if [[ -f .env ]]; then
  chmod 600 .env
  echo ".env yangilandi"
  systemctl restart instagram-operator 2>/dev/null || true
else
  echo ".env topilmadi — setup-env.sh ishlating"
fi
