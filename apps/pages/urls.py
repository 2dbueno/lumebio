from django.urls import path
from . import views

app_name = 'pages'

urlpatterns = [
    path('r/<int:block_id>/', views.block_redirect, name='block_redirect'),
    path('<str:username>/', views.public_page, name='public_page'),
]
