from .base import *
from dotenv import load_dotenv

load_dotenv(BASE_DIR / "swccg" / "settings" / ".env")

# Must be first in INSTALLED_APPS: this is what makes `manage.py runserver` use
# Daphne's ASGI dev server instead of Django's WSGI one. Prod runs gunicorn+uvicorn
# directly instead, so daphne is a dev-only dependency (see pyproject.toml).
INSTALLED_APPS = ["daphne", *INSTALLED_APPS]

DEBUG = True
ALLOWED_HOSTS = ["*"]
SECRET_KEY = 'django-insecure-d-l-io#99wu7o#1ij(%m^9j^==f)$yk1t&k*799&f#5j_yb3r*'

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
DEFAULT_FROM_EMAIL = 'noreply@swccg.local'

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer",
    }
}

# None -> in-memory fallback for live match state (game/state_store.py); prod overrides this.
GAME_REDIS_URL = None

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# CORS_ALLOW_ALL_ORIGINS = True
