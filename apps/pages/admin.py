from django.contrib import admin
from .models import Page, Block, LinkClick


class BlockInline(admin.TabularInline):
    model = Block
    extra = 0
    fields = ['block_type', 'title', 'url', 'is_active', 'order', 'clicks']


@admin.register(Page)
class PageAdmin(admin.ModelAdmin):
    list_display = ['user', 'title', 'theme', 'is_published', 'created_at']
    inlines = [BlockInline]


@admin.register(Block)
class BlockAdmin(admin.ModelAdmin):
    list_display = ['page', 'block_type', 'title', 'is_active', 'order', 'clicks']


@admin.register(LinkClick)
class LinkClickAdmin(admin.ModelAdmin):
    list_display = ['block', 'clicked_at', 'ip_address']
