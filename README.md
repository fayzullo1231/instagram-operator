# Kulol Optom — Instagram AI Operator

Instagram DM va izohlarga avtomatik javob. Mahsulot qidiruv, rasm tahlili, kalit so'z qoidalari.

## Tez boshlash

- **Lokal:** `.\run.ps1` (Windows) yoki `python manage.py runserver`
- **Server:** [DEPLOY.md](DEPLOY.md) — Contabo o'rnatish va endpointlar
- **Panel:** `/panel/` — izoh qoidalari boshqaruvi

## Asosiy endpointlar

| URL | Vazifa |
|-----|--------|
| `POST /api/v1/chat` | Matnli savol |
| `GET /api/v1/instagram/status` | Instagram holati |
| `GET /panel/` | Admin panel |

Batafsil: [DEPLOY.md](DEPLOY.md)
