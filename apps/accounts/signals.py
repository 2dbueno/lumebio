from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from .models import CustomUser, Profile
from .validators import generate_unique_slug


def anonymize_ip(ip: str) -> str:
    """Anonimiza IP para armazenamento — zera último octeto."""
    if not ip:
        return ''
    try:
        parts = ip.split('.')
        if len(parts) == 4:  # IPv4
            parts[-1] = '0'
            return '.'.join(parts)
    except Exception:
        pass
    return ''


@receiver(post_save, sender=CustomUser)
def create_user_profile(sender, instance, created, **kwargs):
    """
    Cria automaticamente um Profile ao criar um CustomUser.

    O IP e o consentimento de marketing são passados via atributos
    temporários no objeto user pela view de registro:
        user._signup_ip = '192.168.1.0'
        user._marketing_consent = True
    """
    if created:
        base_slug = instance.email.split('@')[0]
        slug = generate_unique_slug(base_slug)

        # Dados extras passados pela view de signup (opcionais)
        signup_ip = anonymize_ip(getattr(instance, '_signup_ip', ''))
        marketing_consent = getattr(instance, '_marketing_consent', False)

        profile_kwargs = {
            'slug': slug,
            'signup_ip': signup_ip,
            'marketing_consent': bool(marketing_consent),
        }

        if marketing_consent:
            profile_kwargs['marketing_consent_at'] = timezone.now()

        Profile.objects.create(user=instance, **profile_kwargs)