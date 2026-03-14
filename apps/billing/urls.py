from django.urls import path
from . import views

app_name = 'billing'

urlpatterns = [
    path('', views.portal, name='portal'),
    path('pricing/', views.pricing, name='pricing'),
    path('checkout/', views.checkout, name='checkout'),
    path('success/', views.success, name='success'),
    path('cancel/', views.cancel, name='cancel'),
    path('webhook/', views.webhook, name='webhook'),
]