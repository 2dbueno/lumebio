from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from .models import CustomUser, Profile
from .validators import generate_unique_slug


@receiver(post_save, sender=CustomUser)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        base_slug = instance.email.split('@')[0].lower()
        slug = generate_unique_slug(base_slug)
        Profile.objects.create(
            user=instance,
            slug=slug,
            display_name=base_slug,
        )


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def criar_page_usuario(sender, instance, created, **kwargs):
    if created:
        from apps.pages.models import Page  # import lazy evita circular import
        Page.objects.create(
            user=instance,
            title=instance.profile.slug if hasattr(instance, 'profile') else '',
        )
