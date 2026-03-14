from django.contrib import admin
from .models import Plan, Subscription, Invoice


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'price_monthly', 'max_links', 'is_active']
    prepopulated_fields = {'slug': ('name',)}


class InvoiceInline(admin.TabularInline):
    model = Invoice
    extra = 0
    readonly_fields = ['abacate_billing_id', 'amount', 'status', 'billing_url', 'paid_at', 'reference_month', 'created_at']
    can_delete = False


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ['profile', 'plan', 'status', 'current_period_start', 'current_period_end', 'created_at']
    list_filter = ['status', 'plan']
    search_fields = ['profile__slug', 'profile__user__email']
    readonly_fields = ['abacate_billing_id', 'abacate_customer_id', 'created_at', 'updated_at']
    inlines = [InvoiceInline]


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ['subscription', 'reference_month', 'amount', 'status', 'paid_at', 'created_at']
    list_filter = ['status', 'reference_month']
    readonly_fields = ['abacate_billing_id', 'billing_url', 'paid_at', 'created_at']