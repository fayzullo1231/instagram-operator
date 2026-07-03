import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "django-insecure-change-me-in-production")
DEBUG = os.getenv("APP_ENV", "development") == "development"
ALLOWED_HOSTS = [h.strip() for h in os.getenv("ALLOWED_HOSTS", "*").split(",") if h.strip()]

GUNICORN_BIND = os.getenv("GUNICORN_BIND", "0.0.0.0:8010")
GUNICORN_WORKERS = int(os.getenv("GUNICORN_WORKERS", "2"))

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "shop",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "shop" / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": DATA_DIR / "db.sqlite3",
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
]

LANGUAGE_CODE = "uz"
TIME_ZONE = "Asia/Tashkent"
USE_I18N = True
USE_TZ = True

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "data" / "media"
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "http://127.0.0.1:8010").rstrip("/")
STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "shop" / "static"]
STATIC_ROOT = BASE_DIR / "data" / "static"
LOGIN_URL = "/panel/login/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Application settings
APP_NAME = os.getenv("APP_NAME", "Instagram AI Operator")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
SYNC_INTERVAL_MINUTES = int(os.getenv("SYNC_INTERVAL_MINUTES", "5"))
SYNC_ON_STARTUP = os.getenv("SYNC_ON_STARTUP", "false").lower() == "true"
SYNC_STARTUP_DELAY_SECONDS = int(os.getenv("SYNC_STARTUP_DELAY_SECONDS", "15"))

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")

LINKO_API_URL = os.getenv(
    "LINKO_API_URL",
    "https://kuloloptomuz.linko.uz/ru/api/v1/main/product_list_pos/",
)
LINKO_API_TOKEN = os.getenv("LINKO_API_TOKEN", "")

MDOKON_API_URL = os.getenv(
    "MDOKON_API_URL",
    "https://cabinet.mdokon.uz/services/web/api/report-balance-product-api",
)
MDOKON_API_KEY = os.getenv("MDOKON_API_KEY", "")

TEZPOS_ENABLED = os.getenv("TEZPOS_ENABLED", "true").lower() == "true"
TEZPOS_API_URL = os.getenv("TEZPOS_API_URL", "http://13.140.146.78:8000")
TEZPOS_SERVER_NAME = os.getenv("TEZPOS_SERVER_NAME", "demo")
TEZPOS_API_TOKEN = os.getenv("TEZPOS_API_TOKEN", "")
TEZPOS_LOGIN = os.getenv("TEZPOS_LOGIN", "demo")
TEZPOS_PASSWORD = os.getenv("TEZPOS_PASSWORD", "demo123")

KULOLOPTOM_ENABLED = os.getenv("KULOLOPTOM_ENABLED", "true").lower() == "true"
KULOLOPTOM_SERVER_NAME = os.getenv("KULOLOPTOM_SERVER_NAME", "kuloloptom-2")
KULOLOPTOM_API_TOKEN = os.getenv("KULOLOPTOM_API_TOKEN", "")
KULOLOPTOM_LOGIN = os.getenv("KULOLOPTOM_LOGIN", "")
KULOLOPTOM_PASSWORD = os.getenv("KULOLOPTOM_PASSWORD", "")

INSTAGRAM_ENABLED = os.getenv("INSTAGRAM_ENABLED", "true").lower() == "true"
INSTAGRAM_POLL_INTERVAL_SECONDS = int(os.getenv("INSTAGRAM_POLL_INTERVAL_SECONDS", "30"))
INSTAGRAM_MEDIA_AMOUNT = int(os.getenv("INSTAGRAM_MEDIA_AMOUNT", "5"))
INSTAGRAM_CONVERSATION_LIMIT = int(os.getenv("INSTAGRAM_CONVERSATION_LIMIT", "8"))
INSTAGRAM_MESSAGE_LIMIT = int(os.getenv("INSTAGRAM_MESSAGE_LIMIT", "15"))
INSTAGRAM_MESSAGE_FETCH_LIMIT = int(os.getenv("INSTAGRAM_MESSAGE_FETCH_LIMIT", "50"))
INSTAGRAM_MESSAGE_MAX_PAGES = int(os.getenv("INSTAGRAM_MESSAGE_MAX_PAGES", "10"))
INSTAGRAM_COMMENT_POLL_EVERY = int(os.getenv("INSTAGRAM_COMMENT_POLL_EVERY", "3"))
INSTAGRAM_MAX_MESSAGE_AGE_HOURS = int(os.getenv("INSTAGRAM_MAX_MESSAGE_AGE_HOURS", "72"))
INSTAGRAM_DM_BURST_SECONDS = int(os.getenv("INSTAGRAM_DM_BURST_SECONDS", "90"))
INSTAGRAM_THREAD_REPLY_COOLDOWN_SECONDS = int(os.getenv("INSTAGRAM_THREAD_REPLY_COOLDOWN_SECONDS", "120"))

# Zernio — Instagram DM/izohlar (https://zernio.com)
ZERNIO_API_KEY = os.getenv("ZERNIO_API_KEY", "")
ZERNIO_API_URL = os.getenv("ZERNIO_API_URL", "https://zernio.com/api/v1")
ZERNIO_ACCOUNT_ID = os.getenv("ZERNIO_ACCOUNT_ID", "")
ZERNIO_MIN_REQUEST_INTERVAL_SECONDS = float(os.getenv("ZERNIO_MIN_REQUEST_INTERVAL_SECONDS", "1.1"))
ZERNIO_RATE_LIMIT_MAX_RETRIES = int(os.getenv("ZERNIO_RATE_LIMIT_MAX_RETRIES", "3"))

FUZZ_MIN_SIMILARITY = int(os.getenv("FUZZ_MIN_SIMILARITY", "60"))
FUZZ_TOP_N = int(os.getenv("FUZZ_TOP_N", "5"))
CATEGORY_MATCH_LIMIT = int(os.getenv("CATEGORY_MATCH_LIMIT", "0"))
IMAGE_MATCH_MIN_SCORE = int(os.getenv("IMAGE_MATCH_MIN_SCORE", "90"))
IMAGE_SEARCH_MIN_FUZZ = int(os.getenv("IMAGE_SEARCH_MIN_FUZZ", "85"))

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "standard",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": LOG_LEVEL,
    },
    "loggers": {
        "httpx": {"level": "WARNING"},
        "httpcore": {"level": "WARNING"},
        "apscheduler": {"level": "WARNING"},
        "django.utils.autoreload": {"level": "WARNING"},
        "django.server": {"level": "INFO"},
    },
}
