
"""
DJANGO SETTINGS — AFROFANS
===========================================
Entreprise : HexaQuébec
Projet     : Afrofans
Application: Afrons
Hébergement: Render
Base       : PostgreSQL / SQLite local
===========================================
"""

import os
from pathlib import Path

import dj_database_url
from dotenv import load_dotenv


# ============================================================
# 1. CHEMINS DU PROJET
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")


# ============================================================
# 2. FONCTION UTILITAIRE — VARIABLES BOOLÉENNES
# ============================================================

def env_bool(name, default=False):
    value = os.getenv(name)

    if value is None:
        return default

    return value.strip().lower() in (
        "true",
        "1",
        "yes",
        "on",
    )

# ============================================================
# AFROFANS — ENVIRONNEMENT
# ============================================================

IS_RENDER = env_bool("RENDER", False)

DEBUG = env_bool(
    "DEBUG",
    default=not IS_RENDER,
)

# ============================================================
# 4. SÉCURITÉ DJANGO
# ============================================================

SECRET_KEY = os.getenv("AFROFANS_SECRET_KEY")

if not SECRET_KEY:

    if DEBUG:
        SECRET_KEY = (
            "django-insecure-"
            "afrofans-development-only-change-me"
        )

    else:
        raise RuntimeError(
            "AFROFANS_SECRET_KEY est obligatoire "
            "en production."
        )


# ============================================================
# 5. DOMAINES AUTORISÉS
# ============================================================

ALLOWED_HOSTS = [
    "127.0.0.1",
    "localhost",
    "afrofans.onrender.com",
]

EXTRA_ALLOWED_HOSTS = os.getenv(
    "AFROFANS_ALLOWED_HOSTS",
    "",
)

for host in EXTRA_ALLOWED_HOSTS.split(","):

    host = host.strip()

    if host and host not in ALLOWED_HOSTS:
        ALLOWED_HOSTS.append(host)


# ============================================================
# 6. PROTECTION CSRF
# ============================================================

CSRF_TRUSTED_ORIGINS = [
    "https://afrofans.onrender.com",
]

EXTRA_CSRF_ORIGINS = os.getenv(
    "AFROFANS_CSRF_TRUSTED_ORIGINS",
    "",
)

for origin in EXTRA_CSRF_ORIGINS.split(","):

    origin = origin.strip()

    if origin and origin not in CSRF_TRUSTED_ORIGINS:
        CSRF_TRUSTED_ORIGINS.append(origin)


# ============================================================
# 7. SÉCURITÉ HTTPS / COOKIES
# ============================================================

SECURE_PROXY_SSL_HEADER = (
    "HTTP_X_FORWARDED_PROTO",
    "https",
)

SECURE_SSL_REDIRECT = not DEBUG

SESSION_COOKIE_SECURE = not DEBUG

CSRF_COOKIE_SECURE = not DEBUG

SESSION_COOKIE_HTTPONLY = True

CSRF_COOKIE_HTTPONLY = False

SESSION_COOKIE_SAMESITE = "Lax"

CSRF_COOKIE_SAMESITE = "Lax"

SECURE_CONTENT_TYPE_NOSNIFF = True

X_FRAME_OPTIONS = "DENY"

SECURE_REFERRER_POLICY = "same-origin"

SECURE_HSTS_SECONDS = (
    31536000 if not DEBUG else 0
)

SECURE_HSTS_INCLUDE_SUBDOMAINS = False

SECURE_HSTS_PRELOAD = False


# ============================================================
# 8. APPLICATIONS INSTALLÉES
# ============================================================
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    # Cloudinary
    "cloudinary_storage",
    "cloudinary",

    # AfroFans
    "Afrons.apps.AfronsConfig",
]

# ============================================================
# 9. MIDDLEWARE
# ============================================================

MIDDLEWARE = [

    "django.middleware.security.SecurityMiddleware",

    "whitenoise.middleware.WhiteNoiseMiddleware",

    "django.contrib.sessions.middleware.SessionMiddleware",

    "django.middleware.common.CommonMiddleware",

    "django.middleware.csrf.CsrfViewMiddleware",

    "django.contrib.auth.middleware.AuthenticationMiddleware",

    "django.contrib.messages.middleware.MessageMiddleware",

    "django.middleware.clickjacking.XFrameOptionsMiddleware",

]


# ============================================================
# 10. CONFIGURATION DES URLS
# ============================================================

ROOT_URLCONF = "Afrofans.urls"

WSGI_APPLICATION = "Afrofans.wsgi.application"

ASGI_APPLICATION = "Afrofans.asgi.application"


# ============================================================
# 11. TEMPLATES HTML
# ============================================================

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


# ============================================================
# 12. BASE DE DONNÉES
# POSTGRESQL SUR RENDER
# SQLITE EN DÉVELOPPEMENT
# ============================================================

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "",
)

if DATABASE_URL:

    DATABASES = {

        "default": dj_database_url.parse(
            DATABASE_URL,
            conn_max_age=600,
            conn_health_checks=True,
        )

    }

else:

    if IS_RENDER:
        import warnings

        warnings.warn(
            "AfroFans utilise SQLite sur Render. "
            "Configurer DATABASE_URL avec PostgreSQL "
            "avant toute utilisation en production.",
            RuntimeWarning,
        )

    DATABASES = {

        "default": {

            "ENGINE": "django.db.backends.sqlite3",

            "NAME": BASE_DIR / "db.sqlite3",

        }

    }


# ============================================================
# 13. VALIDATION DES MOTS DE PASSE
# ============================================================

AUTH_PASSWORD_VALIDATORS = [

    {
        "NAME": (
            "django.contrib.auth."
            "password_validation."
            "UserAttributeSimilarityValidator"
        ),
    },

    {
        "NAME": (
            "django.contrib.auth."
            "password_validation."
            "MinimumLengthValidator"
        ),
    },

    {
        "NAME": (
            "django.contrib.auth."
            "password_validation."
            "CommonPasswordValidator"
        ),
    },

    {
        "NAME": (
            "django.contrib.auth."
            "password_validation."
            "NumericPasswordValidator"
        ),
    },

]


# ============================================================
# 14. LANGUE ET FUSEAU HORAIRE
# ============================================================

LANGUAGE_CODE = "fr-ca"

TIME_ZONE = "America/Toronto"

USE_I18N = True

USE_TZ = True


# ============================================================
# 15. FICHIERS STATIQUES
# CSS / JS / IMAGES / LOGOS
# ============================================================

STATIC_URL = "/static/"

STATIC_ROOT = BASE_DIR / "staticfiles"

STATICFILES_DIRS = []

if (BASE_DIR / "static").is_dir():

    STATICFILES_DIRS.append(
        BASE_DIR / "static"
    )


# ============================================================
# 16. STOCKAGE DES FICHIERS STATIQUES
# WHITENOISE
# ============================================================
# ============================================================
# AFROFANS — STOCKAGE CLOUDINARY / RENDER
# ============================================================

CLOUDINARY_URL = os.getenv("CLOUDINARY_URL", "")

STORAGES = {
    "default": {
        "BACKEND": (
            "cloudinary_storage.storage.MediaCloudinaryStorage"
            if CLOUDINARY_URL
            else "django.core.files.storage.FileSystemStorage"
        ),
    },

    "staticfiles": {
        "BACKEND": (
            "whitenoise.storage."
            "CompressedManifestStaticFilesStorage"
        ),
    },
}

# ============================================================
# 17. FICHIERS MULTIMÉDIAS
# VIDÉOS / AVATARS / MINIATURES
# ============================================================

MEDIA_URL = "/media/"

MEDIA_ROOT = BASE_DIR / "media"

# IMPORTANT :
# Ce stockage local n'est pas persistant
# sur un service Render sans disque persistant.
#
# Configurer Cloudinary ou un stockage externe
# avant d'accepter les médias des utilisateurs.


# ============================================================
# 18. CONNEXION / DÉCONNEXION
# ============================================================

LOGIN_URL = "Afrons:connexion"

LOGIN_REDIRECT_URL = "Afrons:flux"

LOGOUT_REDIRECT_URL = "Afrons:flux"


# ============================================================
# 19. FICHIERS TÉLÉVERSÉS
# ============================================================

FILE_UPLOAD_MAX_MEMORY_SIZE = (
    10 * 1024 * 1024
)

DATA_UPLOAD_MAX_MEMORY_SIZE = (
    150 * 1024 * 1024
)


# ============================================================
# 20. CLÉS PRIMAIRES
# ============================================================

DEFAULT_AUTO_FIELD = (
    "django.db.models.BigAutoField"
)


# ============================================================
# 21. IDENTITÉ DU SITE AFROFANS
# ============================================================

SITE_URL = os.getenv(
    "AFROFANS_SITE_URL",
    (
        "https://afrofans.onrender.com"
        if not DEBUG
        else "http://127.0.0.1:8000"
    ),
).rstrip("/")

AFROFANS_PROPRIETAIRE = "HexaQuébec"

AFROFANS_TPS = "0.05"

AFROFANS_TVQ = "0.09975"


# ============================================================
# 22. CONFIGURATION EMAIL — GMAIL
# ============================================================

EMAIL_BACKEND = os.getenv(
    "EMAIL_BACKEND",
    "django.core.mail.backends.smtp.EmailBackend",
)

EMAIL_HOST = os.getenv(
    "EMAIL_HOST",
    "smtp.gmail.com",
)

EMAIL_PORT = int(
    os.getenv(
        "EMAIL_PORT",
        "587",
    )
)

EMAIL_USE_TLS = env_bool(
    "EMAIL_USE_TLS",
    True,
)

EMAIL_USE_SSL = env_bool(
    "EMAIL_USE_SSL",
    False,
)

EMAIL_HOST_USER = os.getenv(
    "EMAIL_HOST_USER",
    "",
)

EMAIL_HOST_PASSWORD = os.getenv(
    "EMAIL_HOST_PASSWORD",
    "",
)

DEFAULT_FROM_EMAIL = (
    f"AfroFans <{EMAIL_HOST_USER}>"
    if EMAIL_HOST_USER
    else "AfroFans <noreply@localhost>"
)

EMAIL_TIMEOUT = 30


# ============================================================
# 23. CELERY
# ============================================================

CELERY_BROKER_URL = os.getenv(
    "CELERY_BROKER_URL",
    "redis://127.0.0.1:6379/0",
)

CELERY_RESULT_BACKEND = os.getenv(
    "CELERY_RESULT_BACKEND",
    "redis://127.0.0.1:6379/0",
)

CELERY_ACCEPT_CONTENT = [
    "json",
]

CELERY_TASK_SERIALIZER = "json"

CELERY_RESULT_SERIALIZER = "json"

# Mode synchrone par défaut.
# Pour les tâches en arrière-plan :
# configurer un worker Celery et Redis.

CELERY_TASK_ALWAYS_EAGER = env_bool(
    "CELERY_TASK_ALWAYS_EAGER",
    True,
)

CELERY_TASK_EAGER_PROPAGATES = DEBUG


# ============================================================
# 24. STOCKAGE PRIVÉ
# DOCUMENTS DE VÉRIFICATION DES TALENTS
# ============================================================

PRIVATE_VERIFICATION_ROOT = Path(
    os.getenv(
        "PRIVATE_VERIFICATION_ROOT",
        str(
            Path.home()
            / "AfroFansPrivate"
            / "verification_talents"
        ),
    )
)

# Ce chemin local n'assure pas la persistance
# sur Render. Les pièces d'identité exigent
# un stockage privé et durable avec
# contrôle d'accès.


# ============================================================
# 25. LIVEKIT
# AUDIO / VIDÉO / PRÉSENCE TEMPS RÉEL
# ============================================================

LIVEKIT_URL = os.getenv(
    "LIVEKIT_URL",
    "",
)

LIVEKIT_API_KEY = os.getenv(
    "LIVEKIT_API_KEY",
    "",
)

LIVEKIT_API_SECRET = os.getenv(
    "LIVEKIT_API_SECRET",
    "",
)


# ============================================================
# 26. STRIPE — CONFIGURATION GÉNÉRALE
# ============================================================

STRIPE_SECRET_KEY = os.getenv(
    "STRIPE_SECRET_KEY",
    "",
)


# ============================================================
# 27. STRIPE — BILLETTERIE
# ============================================================

STRIPE_WEBHOOK_SECRET_BILLETS = os.getenv(
    "STRIPE_WEBHOOK_SECRET_BILLETS",
    "",
)

AFROFANS_DEVISE_BILLETS = os.getenv(
    "AFROFANS_DEVISE_BILLETS",
    "cad",
).lower()

AFROFANS_TAILLE_LOT = int(
    os.getenv(
        "AFROFANS_TAILLE_LOT",
        "20",
    )
)

AFROFANS_TAUX_COMMISSION = os.getenv(
    "AFROFANS_TAUX_COMMISSION",
    "0.05",
)


# ============================================================
# 28. STRIPE — VIDÉOS PAYANTES
# ============================================================

STRIPE_WEBHOOK_SECRET_VIDEOS = os.getenv(
    "STRIPE_WEBHOOK_SECRET_VIDEOS",
    "",
)

AFROFANS_DEVISE_VIDEOS = os.getenv(
    "AFROFANS_DEVISE_VIDEOS",
    "cad",
).lower()

AFROFANS_PAIEMENTS_VIDEOS_ACTIFS = env_bool(
    "AFROFANS_PAIEMENTS_VIDEOS_ACTIFS",
    False,
)


# ============================================================
# 29. AFROFANS — DONS
# ============================================================

AFROFANS_DEVISE_DONS = os.getenv(
    "AFROFANS_DEVISE_DONS",
    "cad",
).lower()

AFROFANS_DONS_ACTIFS = env_bool(
    "AFROFANS_DONS_ACTIFS",
    False,
)


# ============================================================
# 30. VÉRIFICATION DES TALENTS
# ============================================================

AFROFANS_VERIFICATION_PAIEMENT_ACTIF = env_bool(
    "AFROFANS_VERIFICATION_PAIEMENT_ACTIF",
    True,
)


# ============================================================
# 31. STRIPE CONNECT — RETRAITS
# ============================================================
# ==========================================
# AFROFANS — STRIPE CONNECT
# ==========================================

AFROFANS_STRIPE_CONNECT_ACTIF = True

AFROFANS_RETRAITS_ACTIFS = env_bool(
    "AFROFANS_RETRAITS_ACTIFS",
    True,
)


# ============================================================
# 32. JOURNALISATION
# ============================================================

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

        "level": (
            "DEBUG"
            if DEBUG
            else "INFO"
        ),

    },

}


# ============================================================
# FIN — SETTINGS AFROFANS
# HEXAQUÉBEC
# ============================================================



# ============================================================
# AFROFANS — CONVERSION DES FRAIS DE BILLETTERIE
# ============================================================

import os
from decimal import Decimal, InvalidOperation


def lire_taux_conversion(nom):
    valeur = os.environ.get(nom, "").strip()

    if not valeur:
        return None

    try:
        taux = Decimal(valeur)

        if not taux.is_finite() or taux <= 0:
            return None

        return taux

    except (InvalidOperation, ValueError):
        return None


TAUX_XOF_CAD = lire_taux_conversion(
    "TAUX_XOF_CAD"
)

TAUX_XOF_EUR = lire_taux_conversion(
    "TAUX_XOF_EUR"
)
