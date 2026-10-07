"""
Django settings for projecthub_config project.
"""

from pathlib import Path
import os
from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'django-insecure-projecthub-ai-secret-key-development-mode-10-10')

DEBUG = os.getenv('DJANGO_DEBUG', 'False') == 'True'

if not DEBUG and SECRET_KEY.startswith('django-insecure'):
    raise ImproperlyConfigured("DJANGO_SECRET_KEY phải được cấu hình an toàn khi DEBUG=False.")

ALLOWED_HOSTS = [h.strip() for h in os.getenv('DJANGO_ALLOWED_HOSTS', '127.0.0.1,localhost,*.onrender.com,*.ngrok-free.app,*.serveo.net').split(',') if h.strip()]

default_origins = (
    'http://127.0.0.1,http://127.0.0.1:8000,http://127.0.0.1:8088,http://127.0.0.1:8001,'
    'http://localhost,http://localhost:8000,http://localhost:8088,http://localhost:8001,'
    'https://*.onrender.com,https://*.ngrok-free.app,https://*.serveo.net'
)
raw_origins = os.getenv('DJANGO_CSRF_TRUSTED_ORIGINS', default_origins).split(',')
CSRF_TRUSTED_ORIGINS = list(set([o.strip() for o in raw_origins if o.strip()]))

# Ensure common local ports are present in CSRF_TRUSTED_ORIGINS
for port in ['', ':8000', ':8088', ':8001', ':8080', ':3000']:
    CSRF_TRUSTED_ORIGINS.append(f'http://127.0.0.1{port}')
    CSRF_TRUSTED_ORIGINS.append(f'http://localhost{port}')
CSRF_TRUSTED_ORIGINS = list(set(CSRF_TRUSTED_ORIGINS))

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

INSTALLED_APPS = []
try:
    import daphne
    INSTALLED_APPS.append('daphne')
except ImportError:
    pass

INSTALLED_APPS.extend([
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
])

try:
    import channels
    INSTALLED_APPS.append('channels')
except ImportError:
    pass

INSTALLED_APPS.extend([
    # Custom Apps
    'accounts',
    'projects',
    'tasks',
    'milestones',
    'documents',
    'reviews',
    'notifications',
    'ai_assistant',
    'audit_log',
    'dashboard',
])

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
]
try:
    import whitenoise
    MIDDLEWARE.append('whitenoise.middleware.WhiteNoiseMiddleware')
except ImportError:
    pass

MIDDLEWARE.extend([
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'accounts.middleware.ActiveUserMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
])

ROOT_URLCONF = 'projecthub_config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'notifications.context_processors.notification_context',
                'core.context_processors.breadcrumbs',
            ],
        },
    },
]

WSGI_APPLICATION = 'projecthub_config.wsgi.application'

db_url = os.getenv('DATABASE_URL', 'sqlite:///' + str(BASE_DIR / 'db.sqlite3'))
try:
    import dj_database_url
    DATABASES = {
        'default': dj_database_url.config(
            default=db_url,
            conn_max_age=600,
            conn_health_checks=True,
        )
    }
except ImportError:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

import sys
if 'test' in sys.argv:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': ':memory:',
        }
    }

WHITENOISE_MANIFEST_STRICT = False
X_FRAME_OPTIONS = 'SAMEORIGIN'

AUTH_USER_MODEL = 'accounts.User'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {'min_length': 8}
    },
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'vi'
TIME_ZONE = 'Asia/Ho_Chi_Minh'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'dashboard'
LOGOUT_REDIRECT_URL = 'landing'

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# ASGI & Channels Realtime Configuration
ASGI_APPLICATION = 'projecthub_config.asgi.application'

REDIS_URL = os.getenv('REDIS_URL')
if REDIS_URL:
    CHANNEL_LAYERS = {
        'default': {
            'BACKEND': 'channels_redis.core.RedisChannelLayer',
            'CONFIG': {"hosts": [REDIS_URL]},
        }
    }
else:
    CHANNEL_LAYERS = {
        'default': {
            'BACKEND': 'channels.layers.InMemoryChannelLayer',
        }
    }

# Security and Upload limits
FILE_UPLOAD_MAX_MEMORY_SIZE = 20 * 1024 * 1024
DATA_UPLOAD_MAX_MEMORY_SIZE = 20 * 1024 * 1024

if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_BROWSER_XSS_FILTER = True
    if os.getenv('SECURE_SSL_REDIRECT', 'False') == 'True':
        SECURE_SSL_REDIRECT = True

# Celery Configuration
CELERY_BROKER_URL = REDIS_URL or 'memory://'
CELERY_RESULT_BACKEND = REDIS_URL or 'disabled://'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'Asia/Ho_Chi_Minh'
