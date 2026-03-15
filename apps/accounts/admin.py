from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import CustomUser, Profile


class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    verbose_name_plural = 'Perfil'
    fields = ('slug', 'display_name', 'bio', 'plan', 'avatar', 'custom_domain')


@admin.register(CustomUser)
class CustomUserAdmin(BaseUserAdmin):
    inlines = (ProfileInline,)
    list_display = ('email', 'is_active', 'is_staff', 'date_joined')
    list_filter = ('is_active', 'is_staff')
    search_fields = ('email',)
    ordering = ('-date_joined',)
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Permissões', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2', 'is_active', 'is_staff'),
        }),
    )


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ['slug', 'user', 'plan', 'marketing_consent', 'signup_ip', 'created_at']
    list_filter = ['plan', 'marketing_consent']
    search_fields = ['slug', 'user__email']
    readonly_fields = ['signup_ip', 'marketing_consent_at', 'created_at', 'updated_at']