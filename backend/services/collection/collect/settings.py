from pathlib import Path
from decouple import config
import os

BASE_DIR = Path(__file__).resolve().parent.parent

_CI_MODE = os.getenv("CI", "").lower() in ("true", "1", "yes")

SECRET_KEY = config('SECRET_KEY')
DEBUG = config('DEBUG', default=False, cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='').split(',')
KAFKA_BOOTSTRAP_SERVERS = config('KAFKA_BOOTSTRAP_SERVERS', default='kafka:9092')

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'drf_spectacular',
    'corsheaders',
    'collectors',
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "collectors.middleware.UserInjectionMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "collect.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
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

WSGI_APPLICATION = "collect.wsgi.application"

if config("USE_SQLITE_FOR_TESTS", default=False, cast=bool):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "test.sqlite3",
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": config("COLLECTION_DATABASE_NAME"),
            "USER": config("DATABASE_USER"),
            "PASSWORD": config("DATABASE_PASSWORD"),
            "HOST": config("COLLECTION_DATABASE_HOST"),
            "PORT": config("COLLECTION_DATABASE_PORT", default="5434"),
        }
    }

REST_FRAMEWORK = {
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_AUTHENTICATION_CLASSES": [],
    "DEFAULT_PERMISSION_CLASSES": [],
}

# drf-spectacular configuration
SPECTACULAR_SETTINGS = {
    "TITLE": "Collection Service API",
    "DESCRIPTION": "API for collecting data from Git repositories (GitHub, GitLab). "
    "Supports metrics collection, data cleaning, and CSV export.",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
    "SCHEMA_PATH_PREFIX": "/api/",
    "SWAGGER_UI_SETTINGS": {
        "deepLinking": True,
        "persistAuthorization": True,
        "displayOperationId": True,
    },
    "COMPONENT_NO_READ_ONLY_REQUIRED": True,
    "TAGS": [
        {
            "name": "Metrics & Branches",
            "description": "Get available metrics and repository branches",
        },
        {
            "name": "Collection Workflow",
            "description": "Start, configure, and execute data collections",
        },
        {
            "name": "Collection Management",
            "description": "Manage collection status, history, and lifecycle",
        },
        {"name": "Collected Data", "description": "Access raw collected data"},
        {
            "name": "Data Cleaning",
            "description": "Configure and apply data cleaning filters",
        },
        {
            "name": "Cleaned Data",
            "description": "Manage cleaned data instances and CSV exports",
        },
    ],
}

CORS_ALLOWED_ORIGINS = config("CORS_ALLOWED_ORIGINS", default="").split(",")
CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True

CORS_ALLOW_HEADERS = [
    "authorization",
    "content-type",
    "accept",
    "origin",
    "x-user-id",
    "x-requested-with",
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY")
MINIO_BUCKET_NAME = os.getenv("MINIO_BUCKET_NAME")
MINIO_SECURE = os.getenv("MINIO_SECURE", "False").lower() == "true"

# --- Large file upload support (up to 6 GB) ---
DATA_UPLOAD_MAX_MEMORY_SIZE = 6 * 1024 * 1024 * 1024      # 6 GB
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024             # 10 MB – beyond this Django writes to a temp file
FILE_UPLOAD_HANDLERS = [
    'django.core.files.uploadhandler.TemporaryFileUploadHandler',
]
# Logging Configuration
_FILE_LOGGING_ENABLED = (
    not _CI_MODE
    and os.getenv("COLLECTION_ENABLE_FILE_LOGGING", "false").lower()
    in ("true", "1", "yes")
)
_LOG_HANDLERS = ["console", "file"] if _FILE_LOGGING_ENABLED else ["console"]

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "()": "collectors.logging_utils.JSONFormatter",
            "service": "collection",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json",
        },
        **({} if not _FILE_LOGGING_ENABLED else {
            "file": {
                "class": "logging.FileHandler",
                "filename": os.getenv("COLLECTION_LOG_FILE", str(BASE_DIR / "collection.log")),
                "formatter": "json",
            },
        }),
    },
    "root": {
        "handlers": _LOG_HANDLERS,
        "level": "INFO",
    },
    "loggers": {
        "django": {
            "handlers": _LOG_HANDLERS,
            "level": os.getenv("DJANGO_LOG_LEVEL", "WARNING"),
            "propagate": False,
        },
        "django.request": {
            "handlers": _LOG_HANDLERS,
            "level": "INFO",
            "propagate": False,
        },
        "collectors": {
            "handlers": _LOG_HANDLERS,
            "level": "INFO",
            "propagate": False,
        },
    },
}
