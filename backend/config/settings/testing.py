from .base import *  # noqa: F401, F403

DEBUG = False

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": config("DB_NAME", default="wisestay_test"),  # noqa: F405
        "USER": config("DB_USER", default="root"),  # noqa: F405
        "PASSWORD": config("DB_PASSWORD", default=""),  # noqa: F405
        "HOST": config("DB_HOST", default="127.0.0.1"),  # noqa: F405
        "PORT": config("DB_PORT", default="3306"),  # noqa: F405
        "OPTIONS": {
            "charset": "utf8mb4",
        },
    }
}

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer",
    }
}

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}
