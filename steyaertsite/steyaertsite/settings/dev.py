from .base import *
from dotenv import load_dotenv

load_dotenv(BASE_DIR / "steyaertsite" / "settings" / ".env")

DEBUG = True
ALLOWED_HOSTS = ["*"]
SECRET_KEY = 'django-insecure-jm9*6(8xk_06&p@rhc48!xdm!=7=6=s^)xqia2canf-j4$uztp'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# CORS_ALLOW_ALL_ORIGINS = True
