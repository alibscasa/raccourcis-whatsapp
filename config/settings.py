"""Raccourcis WhatsApp — réglages. Tout ce qui est secret vient de l'environnement."""
import os
from pathlib import Path

import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent


def _list(name):
    return [v.strip() for v in os.environ.get(name, '').split(',') if v.strip()]


DEBUG = os.environ.get('DEBUG', '') == '1'
SECRET_KEY = os.environ.get('SECRET_KEY') or ('dev-only-not-secret' if DEBUG else '')
if not SECRET_KEY:
    raise RuntimeError('Variable SECRET_KEY manquante (ou DEBUG=1 en local).')

# Mot de passe unique de l'écran de gestion.
APP_PASSWORD = os.environ.get('APP_PASSWORD', '')

# Green API : identifiants de l'instance reliée au numéro WhatsApp.
GREENAPI_INSTANCE = os.environ.get('GREENAPI_INSTANCE', '')
GREENAPI_TOKEN = os.environ.get('GREENAPI_TOKEN', '')
# L'hôte Green API porte les 4 premiers chiffres de l'instance (ex. 7107.api.greenapi.com).
GREENAPI_URL = os.environ.get('GREENAPI_URL') or (
    f'https://{GREENAPI_INSTANCE[:4]}.api.greenapi.com' if GREENAPI_INSTANCE else '')

# Indicatif ajouté aux numéros saisis au format national (06…, 07…).
COUNTRY_PREFIX = os.environ.get('COUNTRY_PREFIX', '212')

ALLOWED_HOSTS = _list('ALLOWED_HOSTS') or ['*']
CSRF_TRUSTED_ORIGINS = _list('CSRF_TRUSTED_ORIGINS')
for _var in ('RAILWAY_PUBLIC_DOMAIN', 'RENDER_EXTERNAL_HOSTNAME'):
    if os.environ.get(_var):
        CSRF_TRUSTED_ORIGINS.append(f'https://{os.environ[_var]}')

INSTALLED_APPS = [
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'contacts',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'
WSGI_APPLICATION = 'config.wsgi.application'

TEMPLATES = [{
    'BACKEND': 'django.template.backends.django.DjangoTemplates',
    'APP_DIRS': True,
    'OPTIONS': {'context_processors': [
        'django.template.context_processors.request',
        'django.contrib.messages.context_processors.messages',
    ]},
}]

DATABASES = {'default': dj_database_url.config(
    default=f'sqlite:///{BASE_DIR / "db.sqlite3"}', conn_max_age=600)}
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LANGUAGE_CODE = 'fr'
TIME_ZONE = 'Africa/Casablanca'
USE_TZ = True

# Le téléphone reste connecté un an à l'écran de gestion.
SESSION_COOKIE_AGE = 365 * 24 * 3600
SESSION_COOKIE_HTTPONLY = True
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024

if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
