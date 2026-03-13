from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.accounts.models import Profile
from .models import Page


@receiver(post_save, sender=Profile)
def create_user_page(sender, instance, created, **kwargs):
    if created:
        Page.objects.create(
            user=instance.user,
            title=instance.display_name or instance.slug,
        )
