from .base import *
from steyaertsite.settings import get_secret

SECRET_KEY = get_secret("SECRET_KEY")

DEBUG = False
raw_hosts = get_secret("ALLOWED_HOSTS", "")
ALLOWED_HOSTS = [host.strip() for host in raw_hosts.split(",") if host.strip()]

# Add WhiteNoise middleware for production static file serving
MIDDLEWARE.insert(
    MIDDLEWARE.index("django.middleware.security.SecurityMiddleware") + 1,
    "whitenoise.middleware.WhiteNoiseMiddleware"
)

# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases
DATABASES = {
    "default": {
        'ENGINE': f"django.db.backends.{get_secret("DATABASE_ENGINE", "sqlite3")}",
        'NAME': get_secret("DATABASE_NAME", "steyaertsite_db"),
        'USER':get_secret("DATABASE_USERNAME", 'admin'),
        'PASSWORD':get_secret('DATABASE_PASSWORD', "admin"),
        'HOST':get_secret('DATABASE_HOST', 'db'),
        'PORT':get_secret("DATABASE_PORT", 5432)
    }
}


# Security settings
SECURE_SSL_REDIRECT = True
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_SECURE = True

# Trust X-Forwarded-Proto header from nginx-proxy for HTTPS detection
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# CSRF trusted origins for Django 4.0+ behind reverse proxy
csrf_origins = str(get_secret("CSRF_TRUSTED_ORIGINS", "https://movies.steyaert.xyz") or "https://movies.steyaert.xyz")
CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in csrf_origins.split(",")
    if origin.strip()
]

# Additional security headers (optional but recommended)
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True

# WhiteNoise static file storage with compression and caching
STORAGES = {
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}
