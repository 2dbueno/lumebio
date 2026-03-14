from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('allauth.urls')),
    path('accounts/', include('apps.accounts.urls', namespace='accounts')),
    path('dashboard/', include('apps.dashboard.urls')),
    path('analytics/', include('apps.analytics.urls', namespace='analytics')),
    path('billing/', include('apps.billing.urls', namespace='billing')),
    path('privacy/', include('apps.pages.privacy_urls')),
    path('', include('apps.pages.urls', namespace='pages')),
]