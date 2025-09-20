import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(override=True)
PROJECT_DIR = Path(__file__).resolve().parent.parent
BASE_DIR = PROJECT_DIR.parent
WSGI_APPLICATION = "onlydjango.wsgi.application"

FIRST_PARTY_APPS = [
    # the onlydjango folder is actually your project folder
    # However it is added here so that django will pickup the management commands from this directory
    # The management command improves the manage.py startapp command to automatically add apps inside this list
    'onlydjango',
    # Your django apps go below
    'apps.better',
]

THIRD_PARTY_APPS = [
    "django_browser_reload",
    'django_cotton',
    "debug_toolbar",
]

DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.humanize",
    "django.contrib.staticfiles",
    "django.contrib.sites",
    "django.contrib.sitemaps",
]

INSTALLED_APPS = (DJANGO_APPS + THIRD_PARTY_APPS +
                  FIRST_PARTY_APPS)

SITE_ID = 1
CSRF_TRUSTED_ORIGINS = ["https://onlydjango.com", "https://www.onlydjango.com"]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",

    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    # "django.contrib.auth.middleware.LoginRequiredMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "debug_toolbar.middleware.DebugToolbarMiddleware",
    # br
    "django_browser_reload.middleware.BrowserReloadMiddleware",

]

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",  # Default Django authentication
]

INTERNAL_IPS = [
    "127.0.0.1",
]

ROOT_URLCONF = "onlydjango.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [
            os.path.join(PROJECT_DIR, "templates"),
        ],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "onlydjango.helpers.onlydjango_globals.global_settings",
            ],
        },
    },
]

# Password validation
# https://docs.djangoproject.com/en/4.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# Internationalization
# https://docs.djangoproject.com/en/4.2/topics/i18n/

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Indian/Maldives"
USE_I18N = False
USE_TZ = True

# Default primary key field type
# https://docs.djangoproject.com/en/4.2/ref/settings/#default-auto-field
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# All-auth settings
ACCOUNT_LOGIN_METHODS = {"email"}
ACCOUNT_SIGNUP_FIELDS = ['email*', 'password1*', 'password2*']
ACCOUNT_SESSION_REMEMBER = True
ACCOUNT_EMAIL_VERIFICATION = "none"
ACCOUNT_SIGNUP_REDIRECT_URL = "/"
LOGIN_REDIRECT_URL = "/"
SOCIALACCOUNT_EMAIL_AUTHENTICATION = True
SOCIALACCOUNT_STORE_TOKENS = True
SOCIALACCOUNT_ONLY = False



SITE_VERSION = "0.0.1"
SITE_NAME = os.getenv("SITE_NAME")
SITE_AUTHOR = ""
SITE_KEYWORDS = ""
SITE_DESCRIPTION = ""
OG_TYPE = ""
OG_TITLE = ""
OG_DESCRIPTION = ""
OG_IMAGE = ""
TWITTER_CARD = ""
TWITTER_TITLE = ""
TWITTER_DESCRIPTION = ""
TWITTER_IMAGE = ""
