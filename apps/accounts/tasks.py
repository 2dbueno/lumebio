import logging
from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task
def purge_expired_custom_domains():
    """
    Remove domínios customizados de perfis Free cujo grace period de 15 dias expirou.
    Roda diariamente via Celery Beat.
    """
    from apps.accounts.models import Profile

    expired = Profile.objects.filter(
        plan=Profile.PLAN_FREE,
        custom_domain__isnull=False,
        custom_domain_expires_at__lt=timezone.now(),
    )

    count = expired.count()
    expired.update(custom_domain=None, custom_domain_expires_at=None)

    logger.info(f'Domínios expirados removidos: {count}')
    return f'Removidos: {count} domínios expirados.'