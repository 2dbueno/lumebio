from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('page/edit/', views.page_edit, name='page_edit'),
    path('blocks/create/', views.block_create, name='block_create'),
    path('blocks/<int:block_id>/edit/', views.block_edit, name='block_edit'),
    path('blocks/<int:block_id>/delete/', views.block_delete, name='block_delete'),
    path('blocks/<int:block_id>/toggle/', views.block_toggle, name='block_toggle'),
    path('blocks/reorder/', views.block_reorder, name='block_reorder'),
]
