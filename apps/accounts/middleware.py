import logging
from django.utils import timezone

logger = logging.getLogger(__name__)

_BYPASS_PREFIXES = (
    '/admin', '/static', '/media', '/accounts',
    '/dashboard', '/analytics', '/billing', '/r/',
)


class CustomDomainMiddleware:
    """
    Roteia requisições de domínios customizados para a página bio do Profile correspondente.
    Respeita grace period de 15 dias após downgrade.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        host = request.get_host().split(':')[0].lower()

        if self._is_platform_host(host):
            return self.get_response(request)

        if any(request.path.startswith(p) for p in _BYPASS_PREFIXES):
            return self.get_response(request)

        profile = self._get_profile_for_domain(host)
        if profile is None:
            return self.get_response(request)

        from apps.pages.views import public_page
        return public_page(request, username=profile.slug)

    def _is_platform_host(self, host: str) -> bool:
        from django.conf import settings
        from urllib.parse import urlparse
        platform_host = urlparse(settings.SITE_URL).hostname or ''
        return host in ('localhost', '127.0.0.1', platform_host)

    def _get_profile_for_domain(self, host: str):
        from apps.accounts.models import Profile
        try:
            profile = Profile.objects.get(custom_domain=host)
        except Profile.DoesNotExist:
            return None

        # Pro ativo — sem restrição
        if profile.plan == Profile.PLAN_PRO:
            return profile

        # Free com grace period ainda válido
        if (profile.custom_domain_expires_at and
                profile.custom_domain_expires_at > timezone.now()):
            return profile

        return None