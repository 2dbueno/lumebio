import re
from django.core.exceptions import ValidationError

RESERVED_SLUGS = [
    'admin', 'api', 'dashboard', 'editor', 'pricing',
    'login', 'register', 'logout', 'settings', 'billing',
    'analytics', 'themes', 'blog', 'privacy', 'terms',
    'static', 'media', 'sitemap', 'robots', 'favicon',
    'lumebio', 'suporte', 'contato', 'about',
]


def validate_slug_not_reserved(value):
    if value.lower() in RESERVED_SLUGS:
        raise ValidationError(
            f'O nome "{value}" é reservado e não pode ser usado.'
        )


def generate_unique_slug(base_slug):
    from .models import Profile

    # Limpa caracteres inválidos
    slug = re.sub(r'[^a-z0-9_-]', '', base_slug.lower())[:50] or 'user'

    if slug in RESERVED_SLUGS:
        slug = f'user-{slug}'

    final_slug = slug
    counter = 1
    while Profile.objects.filter(slug=final_slug).exists():
        final_slug = f'{slug}{counter}'
        counter += 1

    return final_slug
