"""
Django settings for Afrofans project.

Projet principal : Afrofans
Application principale : Afrons
"""

import os
from pathlib import Path


from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
# Charger les variables du fichier .env

load_dotenv(BASE_DIR / ".env")

# =========================================================
# CHEMINS DU PROJET
# =========================================================

BASE_DIR = Path(__file__).resolve().parent.parent


# =========================================================
# SÉCURITÉ
# =========================================================

SECRET_KEY = os.environ.get(
    "AFROFANS_SECRET_KEY",
    (
        "django-insecure-k@6&@9(zqiz!"
        "rlj7aeow7tgo(9r5yeg-d13!"
        "qdt)3pwny!ir7-"
    ),
)

DEBUG = True

ALLOWED_HOSTS = [
    "127.0.0.1",
    "localhost",
]


# =========================================================
# APPLICATIONS
# =========================================================

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    # Application AfroFans
    "Afrons.apps.AfronsConfig",
]


# =========================================================
# MIDDLEWARE
# =========================================================

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]


# =========================================================
# URLS ET APPLICATIONS SERVEUR
# =========================================================

ROOT_URLCONF = "Afrofans.urls"

WSGI_APPLICATION = "Afrofans.wsgi.application"

ASGI_APPLICATION = "Afrofans.asgi.application"


# =========================================================
# TEMPLATES
# =========================================================

TEMPLATES = [
    {
        "BACKEND": (
            "django.template.backends."
            "django.DjangoTemplates"
        ),

        "DIRS": [
            BASE_DIR / "templates",
        ],

        "APP_DIRS": True,

        "OPTIONS": {
            "context_processors": [
                (
                    "django.template."
                    "context_processors.request"
                ),
                (
                    "django.contrib.auth."
                    "context_processors.auth"
                ),
                (
                    "django.contrib.messages."
                    "context_processors.messages"
                ),
            ],
        },
    },
]


# =========================================================
# BASE DE DONNÉES
# =========================================================

DATABASES = {
    "default": {
        "ENGINE": (
            "django.db.backends.sqlite3"
        ),

        "NAME": BASE_DIR / "db.sqlite3",
    },
}


# =========================================================
# VALIDATION DES MOTS DE PASSE
# =========================================================

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "UserAttributeSimilarityValidator"
        ),
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "MinimumLengthValidator"
        ),
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "CommonPasswordValidator"
        ),
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "NumericPasswordValidator"
        ),
    },
]


# =========================================================
# LANGUE ET FUSEAU HORAIRE
# =========================================================

LANGUAGE_CODE = "fr-ca"

TIME_ZONE = "America/Toronto"

USE_I18N = True

USE_TZ = True


# =========================================================
# FICHIERS STATIQUES
# CSS, JAVASCRIPT, LOGOS ET ICÔNES
# =========================================================

STATIC_URL = "/static/"

STATICFILES_DIRS = [
    BASE_DIR / "static",
]

STATIC_ROOT = BASE_DIR / "staticfiles"


# =========================================================
# FICHIERS IMPORTÉS
# VIDÉOS, AVATARS ET MINIATURES
# =========================================================

MEDIA_URL = "/media/"

MEDIA_ROOT = BASE_DIR / "media"


# =========================================================
# CONNEXION ET DÉCONNEXION
# =========================================================

LOGIN_URL = "Afrons:connexion"

LOGIN_REDIRECT_URL = "Afrons:flux"

LOGOUT_REDIRECT_URL = "Afrons:flux"


# =========================================================
# CONFIGURATION DES FICHIERS TÉLÉVERSÉS
# =========================================================

# Les petits fichiers sont temporairement conservés
# en mémoire jusqu’à 10 Mo.

FILE_UPLOAD_MAX_MEMORY_SIZE = (
    10 * 1024 * 1024
)

# Taille maximale totale d’une requête : 150 Mo.

DATA_UPLOAD_MAX_MEMORY_SIZE = (
    150 * 1024 * 1024
)


# =========================================================
# SÉCURITÉ DES COOKIES EN DÉVELOPPEMENT
# =========================================================

SESSION_COOKIE_HTTPONLY = True

CSRF_COOKIE_HTTPONLY = False

X_FRAME_OPTIONS = "DENY"


# =========================================================
# CLÉ PRIMAIRE PAR DÉFAUT
# =========================================================

DEFAULT_AUTO_FIELD = (
    "django.db.models.BigAutoField"
)


# =========================================================
# CONFIGURATION DU SITE AFROFANS
# =========================================================

SITE_URL = os.environ.get(
    "AFROFANS_SITE_URL",
    "http://127.0.0.1:8000",
)

AFROFANS_PROPRIETAIRE = "HexaQuébec"

AFROFANS_TPS = "0.05"

AFROFANS_TVQ = "0.09975"


# =========================================================
# CONFIGURATION DES COURRIELS
# GMAIL DE HEXAQUÉBEC
# =========================================================

# ==============================================
# AFROFANS - CONFIGURATION EMAIL
# ==============================================

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"

EMAIL_HOST = os.getenv(
    "EMAIL_HOST",
    "smtp.gmail.com"
)

EMAIL_PORT = int(
    os.getenv("EMAIL_PORT", "587")
)

EMAIL_USE_TLS = (
    os.getenv("EMAIL_USE_TLS", "True").lower()
    == "true"
)

EMAIL_USE_SSL = False

EMAIL_HOST_USER = os.getenv(
    "EMAIL_HOST_USER",
    ""
)

EMAIL_HOST_PASSWORD = os.getenv(
    "EMAIL_HOST_PASSWORD",
    ""
)

DEFAULT_FROM_EMAIL = (
    f"HexaQuebec <{EMAIL_HOST_USER}>"
)



# =========================================================
# CONFIGURATION CELERY
# =========================================================

CELERY_BROKER_URL = os.environ.get(
    "CELERY_BROKER_URL",
    "redis://127.0.0.1:6379/0",
)

CELERY_RESULT_BACKEND = os.environ.get(
    "CELERY_RESULT_BACKEND",
    "redis://127.0.0.1:6379/0",
)

CELERY_ACCEPT_CONTENT = [
    "json",
]

CELERY_TASK_SERIALIZER = "json"

CELERY_RESULT_SERIALIZER = "json"

# En développement local, les tâches sont exécutées
# immédiatement. Redis n’est donc pas nécessaire.

CELERY_TASK_ALWAYS_EAGER = True

CELERY_TASK_EAGER_PROPAGATES = True





# ============================================================
# AFROFANS — STOCKAGE PRIVÉ DES DOCUMENTS DE VÉRIFICATION
# ============================================================

import os
from pathlib import Path

PRIVATE_VERIFICATION_ROOT = Path(
    os.environ.get(
        "PRIVATE_VERIFICATION_ROOT",
        str(
            Path.home()
            / "AfroFansPrivate"
            / "verification_talents"
        )
    )
)





LIVEKIT_URL = os.environ.get("LIVEKIT_URL", "")
LIVEKIT_API_KEY = os.environ.get("LIVEKIT_API_KEY", "")
LIVEKIT_API_SECRET = os.environ.get("LIVEKIT_API_SECRET", "")




# ============================================================
# AFROFANS — CONFIGURATION STRIPE
# ============================================================

import os

# Clé secrète Stripe
STRIPE_SECRET_KEY = os.environ.get(
    "STRIPE_SECRET_KEY",
    ""
)

# Secret de signature du webhook Stripe
STRIPE_WEBHOOK_SECRET_BILLETS = os.environ.get(
    "STRIPE_WEBHOOK_SECRET_BILLETS",
    ""
)

# Configuration billetterie AfroFans
AFROFANS_DEVISE_BILLETS = "cad"

# 5 % de commission sur chaque lot de 20 billets
AFROFANS_TAILLE_LOT = 20
AFROFANS_TAUX_COMMISSION = "0.05"




STRIPE_WEBHOOK_SECRET_VIDEOS = os.getenv(
    "STRIPE_WEBHOOK_SECRET_VIDEOS",
    ""
)

AFROFANS_PAIEMENTS_VIDEOS_ACTIFS = (
    os.getenv(
        "AFROFANS_PAIEMENTS_VIDEOS_ACTIFS",
        "False"
    ).lower() == "true"
)
