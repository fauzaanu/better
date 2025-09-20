from os import path
from .base import *

DEBUG = True
ALLOWED_HOSTS = [
    "*",
]
SECRET_KEY = "1234"

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.1/howto/static-files/

# Use any S3 Compatible storage backend for static and media files
# AWS_STORAGE_BUCKET_NAME = os.getenv("AWS_STORAGE_BUCKET_NAME")
# AWS_S3_ENDPOINT_URL = os.getenv("AWS_S3_ENDPOINT_URL")
# AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
# AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
# AWS_S3_SIGNATURE_VERSION = "s3v4"
# AWS_S3_CUSTOM_DOMAIN = "cdn.onlydjango.com"
S3_STORAGE = False

if not S3_STORAGE:
    STORAGES = {
        "default": {
            "BACKEND": "django.core.files.storage.FileSystemStorage",
            "OPTIONS": {},
        },
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
            "OPTIONS": {
                "location": path.join(BASE_DIR, "staticfiles"),  # noqa
                "base_url": "/static/",
            },
        },
        # this is development so serve media files locally
        "media": {
            "BACKEND": "django.core.files.storage.FileSystemStorage",
            "OPTIONS": {
                "location": path.join(BASE_DIR, "media"),  # noqa
                "base_url": "/media/",
            },
        },
    }
else:
    STORAGES = {
        'default': {
            'BACKEND': 'storages.backends.s3.S3Storage',
            'OPTIONS': {},
        },
        'staticfiles': {
            'BACKEND': 'storages.backends.s3.S3Storage',
            'OPTIONS': {},
        },
        'media': {
            'BACKEND': 'storages.backends.s3.S3Storage',
            'OPTIONS': {},
        },
    }

STATIC_URL = 'static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')  # noqa
STATICFILES_DIRS = [
    os.path.join(PROJECT_DIR, 'static'),  # noqa
]

# Database
# https://docs.djangoproject.com/en/5.0/ref/settings/#databases
# SQLite
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# Cache settings
# https://docs.djangoproject.com/en/5.0/topics/cache/#setting-up-the-cache
# Using dummy cache for local development
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.dummy.DummyCache",
    }
}


LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "root": {
        "level": "INFO",
        "handlers": ["console"],
        "propagate": "True",
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
        },
    },
}
