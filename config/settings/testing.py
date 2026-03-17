from .base import *
import os

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME':     os.environ.get('POSTGRES_DB',       'lumebio'),
        'USER':     os.environ.get('POSTGRES_USER',     'lumebio'),
        'PASSWORD': os.environ.get('POSTGRES_PASSWORD', 'lumebio123'),
        'HOST':     os.environ.get('POSTGRES_HOST',     'localhost'),
        'PORT':     os.environ.get('POSTGRES_PORT',     '5432'),
    }
}

REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
CELERY_TASK_ALWAYS_EAGER = True
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'

STORAGES = {
    'default': {
        'BACKEND': 'django.core.files.storage.InMemoryStorage',
    },
    'staticfiles': {
        'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage',
    },
}

ABACATEPAY_WEBHOOK_SECRET = 'ci-webhook-secret'