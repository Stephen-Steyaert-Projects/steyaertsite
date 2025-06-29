from .base import *
from steyaertsite.settings import get_secret

SECRET_KEY = get_secret("SECRET_KEY")
ENCRYPTION_KEY = get_secret("ENCRYPTION_KEY")

DEBUG = False
raw_hosts = get_secret("ALLOWED_HOSTS", "")
ALLOWED_HOSTS = [host.strip() for host in raw_hosts.split(",") if host.strip()]

# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases
DATABASES = {
    "default": {
        'ENGINE': f"django.db.backends.{get_secret("DATABASE_ENGINE", "sqlite3")}",
        'NAME': get_secret("DATABASE_NAME", "bibleqna"),
        'USER':get_secret("DATABASE_USERNAME", 'admin'),
        'PASSWORD':get_secret('DATABASE_PASSWORD', "admin"),
        'HOST':get_secret('DATABASE_HOST', 'db'),
        'PORT':get_secret("DATABASE_PORT", 5432)
    }
}


SECURE_SSL_REDIRECT = True
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_SECURE = True

# CORS_ALLOW_ALL_ORIGINS = bool(get_secret("CORS_ALLOW_ALL_ORIGINS", 0))
# CORS_ALLOW_NULL_ORIGIN = bool(get_secret("CORS_ALLOW_NULL_ORIGIN", 1))
# CORS_ALLOWED_ORIGINS = [get_secret("CORS_ALLOWED_ORIGINS", "")]
