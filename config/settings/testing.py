from .base import *

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'lumebio',
        'USER': 'lumebio',
        'PASSWORD': 'lumebio123',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}

REDIS_URL = 'redis://localhost:6379/0'
CELERY_TASK_ALWAYS_EAGER = True
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
