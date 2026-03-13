import os
from django.core.wsgi import get_wsgi_application
from decouple import config

os.environ.setdefault(
    'DJANGO_SETTINGS_MODULE',
    config('DJANGO_SETTINGS_MODULE', default='config.settings.development')
)

application = get_wsgi_application()
