from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('allauth.urls')),
    path('dashboard/', include('apps.dashboard.urls')),
    path('', include('apps.dashboard.urls')),  # temporário até ter landing page
]
