#!/usr/bin/env bash
# Admin panel superuser yaratish
# Ishlatish: bash deploy/create-admin.sh
# Yoki: ADMIN_USER=admin ADMIN_PASS=yourpass bash deploy/create-admin.sh
set -euo pipefail

APP_DIR="/opt/instagram-operator"
cd "$APP_DIR"

ADMIN_USER="${ADMIN_USER:-admin}"
ADMIN_EMAIL="${ADMIN_EMAIL:-admin@kuloloptom.uz}"
ADMIN_PASS="${ADMIN_PASS:-}"

if [[ -z "$ADMIN_PASS" ]]; then
  echo "Parol kiriting (ekranda ko'rinmaydi):"
  read -rs ADMIN_PASS
  echo
fi

if [[ -z "$ADMIN_PASS" ]]; then
  echo "Parol bo'sh bo'lishi mumkin emas"
  exit 1
fi

PYTHON="venv/bin/python"
if [[ ! -x "$PYTHON" ]]; then
  echo "Xato: $APP_DIR/venv topilmadi. Avval: bash deploy/fix-venv.sh"
  exit 1
fi

export DJANGO_SUPERUSER_PASSWORD="$ADMIN_PASS"
export SCHEDULER_ENABLED=false

if $PYTHON manage.py createsuperuser \
  --noinput \
  --username "$ADMIN_USER" \
  --email "$ADMIN_EMAIL" 2>/dev/null; then
  echo "Superuser '$ADMIN_USER' yaratildi"
else
  $PYTHON manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
u, created = User.objects.get_or_create(
    username='$ADMIN_USER',
    defaults={'email': '$ADMIN_EMAIL', 'is_staff': True, 'is_superuser': True},
)
u.set_password('$ADMIN_PASS')
u.is_staff = True
u.is_superuser = True
u.email = '$ADMIN_EMAIL'
u.save()
print('Yaratildi' if created else 'Parol yangilandi')
"
fi

IP=$(hostname -I 2>/dev/null | awk '{print $1}')
echo ""
echo "Panel: http://${IP:-13.140.146.78}:8010/panel/"
echo "Login: $ADMIN_USER"
