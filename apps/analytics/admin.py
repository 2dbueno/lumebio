from django.contrib import admin
from .models import PageView, DailyAggregate


@admin.register(PageView)
class PageViewAdmin(admin.ModelAdmin):
    list_display = ['page', 'viewed_at', 'ip_anon', 'device_type', 'referer_domain']
    list_filter = ['device_type', 'viewed_at']
    search_fields = ['ip_anon', 'referer_domain']
    readonly_fields = ['page', 'viewed_at', 'ip_anon', 'device_type', 'referer_domain']
    ordering = ['-viewed_at']


@admin.register(DailyAggregate)
class DailyAggregateAdmin(admin.ModelAdmin):
    list_display = ['page', 'date', 'total_views', 'total_clicks', 'mobile_count', 'desktop_count', 'top_referer']
    list_filter = ['date']
    readonly_fields = ['page', 'date', 'total_views', 'total_clicks', 'mobile_count', 'desktop_count', 'tablet_count', 'top_referer']
    ordering = ['-date']