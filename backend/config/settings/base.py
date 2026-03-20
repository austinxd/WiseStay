import os
from datetime import timedelta
from pathlib import Path

from decouple import Csv, config

BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = config("SECRET_KEY")

ALLOWED_HOSTS = config("ALLOWED_HOSTS", default="localhost,127.0.0.1", cast=Csv())

# ---------------------------------------------------------------------------
# Application definition
# ---------------------------------------------------------------------------

DJANGO_APPS = [
    "daphne",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "django_filters",
    "corsheaders",
    "django_celery_beat",
    "channels",
]

LOCAL_APPS = [
    "common",
    "apps.accounts",
    "apps.properties",
    "apps.hostaway",
    "apps.reservations",
    "apps.payments",
    "apps.loyalty",
    "apps.domotics",
    "apps.chatbot",
    "apps.owners",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    "common.middleware.request_id.RequestIDMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
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
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": config("DB_NAME", default="wisestay"),
        "USER": config("DB_USER", default="root"),
        "PASSWORD": config("DB_PASSWORD", default=""),
        "HOST": config("DB_HOST", default="127.0.0.1"),
        "PORT": config("DB_PORT", default="3306"),
        "OPTIONS": {
            "charset": "utf8mb4",
            "init_command": "SET sql_mode='STRICT_TRANS_TABLES'",
        },
    }
}

# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ---------------------------------------------------------------------------
# Internationalization
# ---------------------------------------------------------------------------

LANGUAGE_CODE = "en-us"
TIME_ZONE = "America/New_York"
USE_I18N = True
USE_TZ = True

# ---------------------------------------------------------------------------
# Static & Media
# ---------------------------------------------------------------------------

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------------------------------------------------------------------------
# Django REST Framework
# ---------------------------------------------------------------------------

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_PAGINATION_CLASS": "common.pagination.StandardResultsSetPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_FILTER_BACKENDS": (
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ),
    "DEFAULT_THROTTLE_CLASSES": (
        "common.throttles.RoleBasedRateThrottle",
    ),
    "DEFAULT_THROTTLE_RATES": {
        "guest": "100/min",
        "owner": "200/min",
        "admin": "500/min",
        "webhook": "500/min",
        "anon": "30/min",
    },
    "EXCEPTION_HANDLER": "common.exceptions.custom_exception_handler",
}

# ---------------------------------------------------------------------------
# Simple JWT
# ---------------------------------------------------------------------------

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=60),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
}

# ---------------------------------------------------------------------------
# Celery
# ---------------------------------------------------------------------------

CELERY_BROKER_URL = config("REDIS_URL", default="redis://127.0.0.1:6379/0")
CELERY_RESULT_BACKEND = config("REDIS_URL", default="redis://127.0.0.1:6379/0")
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE
CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"

from celery.schedules import crontab  # noqa: E402

CELERY_BEAT_SCHEDULE = {
    "sync-listings-every-6h": {
        "task": "apps.hostaway.tasks.sync_listings_task",
        "schedule": crontab(minute=0, hour="*/6"),
    },
    "sync-reservations-every-15min": {
        "task": "apps.hostaway.tasks.sync_reservations_task",
        "schedule": crontab(minute="*/15"),
    },
    "sync-calendar-every-2h": {
        "task": "apps.hostaway.tasks.sync_calendar_task",
        "schedule": crontab(minute=30, hour="*/2"),
    },
    "expire-points-daily": {
        "task": "apps.loyalty.tasks.expire_points_daily",
        "schedule": crontab(minute=0, hour=2),
    },
    "expire-referrals-daily": {
        "task": "apps.loyalty.tasks.expire_stale_referrals_daily",
        "schedule": crontab(minute=30, hour=2),
    },
    "generate-checkin-codes-hourly": {
        "task": "apps.domotics.tasks.generate_upcoming_checkin_codes",
        "schedule": crontab(minute=0),
    },
    "revoke-checkout-codes-hourly": {
        "task": "apps.domotics.tasks.revoke_checkout_codes",
        "schedule": crontab(minute=30),
    },
    "refresh-device-statuses": {
        "task": "apps.domotics.tasks.refresh_all_device_statuses",
        "schedule": crontab(minute="*/30"),
    },
    "generate-monthly-payouts": {
        "task": "apps.payments.tasks.generate_monthly_payouts_task",
        "schedule": crontab(minute=0, hour=6, day_of_month=1),
    },
    "execute-monthly-payouts": {
        "task": "apps.payments.tasks.execute_payouts_task",
        "schedule": crontab(minute=0, hour=10, day_of_month=5),
    },
    "cancel-expired-pending-reservations": {
        "task": "apps.payments.tasks.cancel_expired_pending_reservations",
        "schedule": crontab(minute=15),
    },
}

# ---------------------------------------------------------------------------
# Django Channels
# ---------------------------------------------------------------------------

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [config("REDIS_URL", default="redis://127.0.0.1:6379/1")],
        },
    },
}

# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": config("REDIS_URL", default="redis://127.0.0.1:6379/2"),
    }
}

# ---------------------------------------------------------------------------
# Encryption key (Fernet)
# ---------------------------------------------------------------------------

ENCRYPTION_KEY = config("ENCRYPTION_KEY")

# ---------------------------------------------------------------------------
# Third-party service keys
# ---------------------------------------------------------------------------

STRIPE_SECRET_KEY = config("STRIPE_SECRET_KEY", default="")
STRIPE_PUBLISHABLE_KEY = config("STRIPE_PUBLISHABLE_KEY", default="")
STRIPE_WEBHOOK_SECRET = config("STRIPE_WEBHOOK_SECRET", default="")
STRIPE_CURRENCY = "usd"

OPENAI_API_KEY = config("OPENAI_API_KEY", default="")
OPENAI_MODEL = config("OPENAI_MODEL", default="gpt-4o")

WHATSAPP_API_URL = config("WHATSAPP_API_URL", default="")
WHATSAPP_API_TOKEN = config("WHATSAPP_API_TOKEN", default="")
WHATSAPP_PHONE_NUMBER_ID = config("WHATSAPP_PHONE_NUMBER_ID", default="")
WHATSAPP_VERIFY_TOKEN = config("WHATSAPP_VERIFY_TOKEN", default="")

HOSTAWAY_API_URL = config("HOSTAWAY_API_URL", default="https://api.hostaway.com/v1")

SEAM_API_KEY = config("SEAM_API_KEY", default="")
