from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.text import slugify

from .models import CustomUser, Profile


@receiver(post_save, sender=CustomUser)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        base_slug = slugify(instance.email.split('@')[0])
        slug = base_slug
        counter = 1

        while Profile.objects.filter(slug=slug).exists():
            slug = f'{base_slug}{counter}'
            counter += 1

        Profile.objects.create(user=instance, slug=slug)