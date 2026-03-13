from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.text import slugify

from .models import CustomUser, Profile

RESERVED_SLUGS = [
    'admin', 'dashboard', 'api', 'login', 'logout', 'register',
    'signup', 'settings', 'profile', 'static', 'media', 'accounts',
    'billing', 'support', 'help', 'about', 'terms', 'privacy',
]


@receiver(post_save, sender=CustomUser)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        base_slug = slugify(instance.email.split('@')[0])
        slug = base_slug
        counter = 1

        while Profile.objects.filter(slug=slug).exists() or slug in RESERVED_SLUGS:
            slug = f'{base_slug}{counter}'
            counter += 1

        Profile.objects.create(user=instance, slug=slug)
