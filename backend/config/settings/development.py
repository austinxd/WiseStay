from .base import *  # noqa: F401, F403

DEBUG = True

CORS_ALLOW_ALL_ORIGINS = True

INSTALLED_APPS += ["debug_toolbar"]  # noqa: F405

MIDDLEWARE.insert(  # noqa: F405
    MIDDLEWARE.index("django.middleware.common.CommonMiddleware") + 1,  # noqa: F405
    "debug_toolbar.middleware.DebugToolbarMiddleware",
)

INTERNAL_IPS = ["127.0.0.1"]

# Use SQLite for local development if MySQL is not available
try:
    import MySQLdb  # noqa: F401
except ImportError:
    DATABASES = {  # noqa: F405
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",  # noqa: F405
        }
    }

# Use in-memory cache if Redis is not available
try:
    import redis as _redis
    _r = _redis.Redis()
    _r.ping()
except Exception:
    CACHES = {  # noqa: F405
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        }
    }

# Faster password hashing for tests
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]
