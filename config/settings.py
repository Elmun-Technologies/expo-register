from pathlib import Path
import os

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")


# --------------------------------------------------
# Core Security Settings
# --------------------------------------------------
# These now come from environment variables so the project is
# production-ready out of the box. Sensible development defaults
# are used automatically when the variables are not set, so
# `python manage.py runserver` keeps working with zero setup.
# See .env.example for the full list of variables.

SECRET_KEY = os.getenv(
    "DJANGO_SECRET_KEY",
    "django-insecure-event-management-system-dev-only",
)

DEBUG = os.getenv("DJANGO_DEBUG", "True") == "True"

ALLOWED_HOSTS = [
    host.strip()
    for host in os.getenv("DJANGO_ALLOWED_HOSTS", "").split(",")
    if host.strip()
]

if DEBUG and not ALLOWED_HOSTS:
    # Local development only. In production, ALLOWED_HOSTS must
    # always be supplied explicitly via the environment.
    ALLOWED_HOSTS = ["localhost", "127.0.0.1"]

CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.getenv("DJANGO_CSRF_TRUSTED_ORIGINS", "").split(",")
    if origin.strip()
]

if DEBUG:
    # Arena sandbox live-preview proxy (https://{port}-{id}.e2b.app).
    ALLOWED_HOSTS += ["*"]
    CSRF_TRUSTED_ORIGINS += [
        "https://*.e2b.app",
        "http://*.e2b.app",
    ]


# --------------------------------------------------
# Applications
# --------------------------------------------------

INSTALLED_APPS = [
    # Third Party
    "crispy_forms",
    "crispy_bootstrap5",

    # Local Apps
    "core",
    "accounts",
    "events",
    "registrations",
    "dashboard",
    "notifications",
    "chatbot",
    "feedback",
    "faq",
    "messaging",
    "expo",

    # Django Apps
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
]


# --------------------------------------------------
# Middleware
# --------------------------------------------------

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


# --------------------------------------------------
# Templates
# --------------------------------------------------

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "notifications.context_processors.notification_context",
                'core.context_processors.dashboard_context',
            ],
        },
    },
]


WSGI_APPLICATION = "config.wsgi.application"


# --------------------------------------------------
# Database
# --------------------------------------------------

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}


# --------------------------------------------------
# Password Validation
# --------------------------------------------------

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


# --------------------------------------------------
# Internationalization
# --------------------------------------------------

LANGUAGE_CODE = "en-us"

TIME_ZONE = "Asia/Tashkent"

USE_I18N = True

USE_TZ = True

# O'zbekiston standartlari: hafta dushanbadan boshlanadi,
# sana/kun formati mahalliy ko'rinishda.
FIRST_DAY_OF_WEEK = 1

DATE_FORMAT = "d.m.Y"

DATETIME_FORMAT = "d.m.Y H:i"

TIME_FORMAT = "H:i"

SHORT_DATE_FORMAT = "d.m.Y"

DECIMAL_SEPARATOR = "."

THOUSAND_SEPARATOR = " "

USE_THOUSAND_SEPARATOR = True


# --------------------------------------------------
# Static Files
# --------------------------------------------------

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

STATICFILES_DIRS = [
    BASE_DIR / "static",
]


# --------------------------------------------------
# Media Files
# --------------------------------------------------

MEDIA_URL = "/media/"

MEDIA_ROOT = BASE_DIR / "media"


# --------------------------------------------------
# Authentication
# --------------------------------------------------

AUTH_USER_MODEL = "accounts.User"

LOGIN_URL = "login"

LOGIN_REDIRECT_URL = "dashboard_home"

LOGOUT_REDIRECT_URL = "home"


# --------------------------------------------------
# Crispy Forms
# --------------------------------------------------

CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"

CRISPY_TEMPLATE_PACK = "bootstrap5"


# --------------------------------------------------
# Email Configuration
# --------------------------------------------------
# Development:
# Emails are printed in the terminal.
# No SMTP setup is required while developing.

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

DEFAULT_FROM_EMAIL = "Expo Control <noreply@expocontrol.uz>"

SERVER_EMAIL = DEFAULT_FROM_EMAIL


# --------------------------------------------------
# Production SMTP Example
# --------------------------------------------------
# Replace the values below and comment out the
# console backend above when deploying.

# EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
# EMAIL_HOST = "smtp.gmail.com"
# EMAIL_PORT = 587
# EMAIL_HOST_USER = "your_email@gmail.com"
# EMAIL_HOST_PASSWORD = "your_app_password"
# EMAIL_USE_TLS = True
# DEFAULT_FROM_EMAIL = EMAIL_HOST_USER


# --------------------------------------------------
# Security (Production)
# --------------------------------------------------
# Automatically hardened whenever DEBUG=False, so a production
# deployment is secure by default without extra steps. These stay
# relaxed in local development so http://127.0.0.1:8000 keeps
# working without HTTPS.

SECURE_SSL_REDIRECT = not DEBUG
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG

SECURE_HSTS_SECONDS = 60 * 60 * 24 * 30 if not DEBUG else 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = not DEBUG
SECURE_HSTS_PRELOAD = not DEBUG

SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"


DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --------------------------------------------------
# Gemini AI
# --------------------------------------------------

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")


# --------------------------------------------------
# Telegram notifications (Uzbekistan market)
# --------------------------------------------------

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")

TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")


# --------------------------------------------------
# SMS notifications — Eskiz.uz (Uzbekistan)
# --------------------------------------------------

ESKIZ_EMAIL = os.getenv("ESKIZ_EMAIL", "")

ESKIZ_PASSWORD = os.getenv("ESKIZ_PASSWORD", "")

ESKIZ_FROM = os.getenv("ESKIZ_FROM", "4546")


# --------------------------------------------------
# Logging
# --------------------------------------------------
# Errors always print to the console (visible in server logs /
# `runserver` output), so problems in production are never
# silently swallowed once DEBUG=False turns off the debug page.

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "django.request": {
            "handlers": ["console"],
            "level": "ERROR",
            "propagate": False,
        },
    },
}