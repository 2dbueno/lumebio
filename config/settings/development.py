from .base import *
import dj_database_url
from decouple import config

DEBUG = True

DATABASES = {
    'default': dj_database_url.config(
        default=config('DATABASE_URL')
    )
}

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

INTERNAL_IPS = ['127.0.0.1']

CORS_ALLOW_ALL_ORIGINS = True
