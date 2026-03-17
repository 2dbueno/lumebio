from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('settings/data/export/',         views.data_export,          name='data_export'),
    path('settings/data/delete/',         views.data_delete_confirm,  name='data_delete_confirm'),
    path('settings/data/delete/confirm/', views.data_delete,          name='data_delete'),
    path('settings/domain/',              views.domain_settings,      name='domain_settings'),
]