from .base import *
from dotenv import load_dotenv

load_dotenv(BASE_DIR / "swccg" / "settings" / ".env")

DEBUG = True
ALLOWED_HOSTS = ["*"]
SECRET_KEY = 'django-insecure-d-l-io#99wu7o#1ij(%m^9j^==f)$yk1t&k*799&f#5j_yb3r*'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# CORS_ALLOW_ALL_ORIGINS = True
