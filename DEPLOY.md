# Kulol Optom — Instagram AI Operator

Instagram DM/izohlar uchun AI operator. Mahsulot qidiruv, rasm tahlili, kalit so'z qoidalari.

## Contabo serverda o'rnatish (13.140.146.78)

### 1. GitHub ga yuklash (kompyuterdan)

```powershell
cd C:\Users\User\Documents\instagram
git init
git add .
git commit -m "Instagram AI operator — production ready"
git branch -M main
git remote add origin https://github.com/SIZNING_USER/instagram-operator.git
git push -u origin main
```

### 2. Serverga birinchi marta o'rnatish

SSH orqali serverga kiring:

```bash
ssh root@13.140.146.78
```

O'rnatish:

```bash
export REPO_URL=https://github.com/SIZNING_USER/instagram-operator.git
sudo bash -c "$(curl -fsSL https://raw.githubusercontent.com/SIZNING_USER/instagram-operator/main/deploy/install.sh)"
```

Yoki qo'lda:

```bash
git clone https://github.com/SIZNING_USER/instagram-operator.git /opt/instagram-operator
cd /opt/instagram-operator
sudo useradd --system --home-dir /opt/instagram-operator instagram 2>/dev/null || true
sudo chown -R instagram:instagram /opt/instagram-operator
sudo -u instagram python3 -m venv venv
sudo -u instagram venv/bin/pip install -r requirements.txt
cp .env.example .env
nano .env   # API kalitlarni kiriting
sudo -u instagram venv/bin/python manage.py migrate
sudo -u instagram venv/bin/python manage.py createsuperuser
sudo cp deploy/instagram-operator.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now instagram-operator
```

### 3. Serverda yangilash (git pull)

Har safar kod yangilanganda:

```bash
cd /opt/instagram-operator
bash deploy/update.sh
```

Yoki qisqa:

```bash
cd /opt/instagram-operator && git pull && venv/bin/pip install -r requirements.txt -q && venv/bin/python manage.py migrate --noinput && sudo systemctl restart instagram-operator
```

### 4. .env sozlash (serverda)

```bash
nano /opt/instagram-operator/.env
```

Muhim:

```env
APP_ENV=production
ALLOWED_HOSTS=13.140.146.78,localhost
SCHEDULER_ENABLED=true
DJANGO_SECRET_KEY=uzun-tasodifiy-kalit
ZERNIO_API_KEY=sk_...
TEZPOS_API_URL=http://127.0.0.1:8000
```

### 5. Port

| Xizmat | Port |
|--------|------|
| TezPOS backend | 8000 |
| **Instagram operator** | **8010** |

---

## API Endpointlar

Baza URL: `http://13.140.146.78:8010`

| Method | Endpoint | Tavsif |
|--------|----------|--------|
| GET | `/health` | Server holati |
| GET | `/ready` | Tayyorlik |
| POST | `/api/v1/chat` | Matnli chat `{"message": "tushonka bormi"}` |
| POST | `/api/v1/sync` | Mahsulotlarni sinxronlash |
| GET | `/api/v1/sync/status` | Sync statistikasi |
| GET | `/api/v1/instagram/status` | Instagram ulanish holati |
| POST | `/api/v1/instagram/poll` | Qo'lda Instagram poll |
| GET | `/panel/` | Admin panel (login kerak) |
| GET | `/panel/login/` | Panel kirish |
| GET | `/panel/videos/` | Video/postlar |
| GET | `/panel/rules/` | Izoh kalit so'z qoidalari |
| GET | `/panel/products/` | Mahsulotlar ro'yxati |
| GET | `/admin/` | Django admin |

### Misollar

```bash
# Health
curl http://13.140.146.78:8010/health

# Chat
curl -X POST http://13.140.146.78:8010/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Assalomu alaykum"}'

# Sync
curl -X POST http://13.140.146.78:8010/api/v1/sync

# Instagram holati
curl http://13.140.146.78:8010/api/v1/instagram/status
```

### Panel

```
http://13.140.146.78:8010/panel/
```

---

## Lokal ishga tushirish (Windows)

```powershell
.\run.ps1
```

## Foydali buyruqlar (serverda)

```bash
# Loglar
sudo journalctl -u instagram-operator -f

# Qayta ishga tushirish
sudo systemctl restart instagram-operator

# Instagram tekshiruv
cd /opt/instagram-operator && sudo -u instagram venv/bin/python manage.py instagram_check

# Cache tozalash
sudo -u instagram venv/bin/python manage.py clear_instagram_cache
```
