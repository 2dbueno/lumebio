from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import F
from apps.accounts.models import Profile
from apps.analytics.tasks import record_page_view
from apps.analytics.utils import anonymize_ip
from .models import Page, Block, LinkClick

def get_client_ip(request):
    """
    Retorna o IP real do visitante.
    Em produção (Nginx), lê X-Forwarded-For.
    Em dev (sem proxy), usa REMOTE_ADDR.
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '')


def public_page(request, username):
    profile = get_object_or_404(Profile, slug=username)
    page = get_object_or_404(Page, user=profile.user, is_published=True)
    blocks = page.blocks.filter(is_active=True).order_by('order')

    # Captura PageView assíncrono se visitante aceitou consentimento LGPD
    consent = request.COOKIES.get('biolink_consent')
    if consent == 'accepted':
        record_page_view.delay(
            page_id=page.id,
            ip=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            referer=request.META.get('HTTP_REFERER', ''),
        )

    return render(request, 'pages/public_page.html', {
        'page': page,
        'blocks': blocks,
        'profile': profile,
    })


def block_redirect(request, block_id):
    block = get_object_or_404(Block, id=block_id, is_active=True)
    consent = request.COOKIES.get('biolink_consent')

    if consent == 'accepted':
        LinkClick.objects.create(
            block=block,
            ip_address=anonymize_ip(get_client_ip(request)),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            referer=request.META.get('HTTP_REFERER', ''),
        )
        # F() expression: UPDATE atômico no banco, sem race condition
        Block.objects.filter(id=block.id).update(clicks=F('clicks') + 1)

    return redirect(block.url)