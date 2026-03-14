import json
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.utils import timezone

from apps.pages.models import Page, Block, LinkClick
from apps.analytics.models import PageView, DailyAggregate


@login_required
def data_export(request):
    """
    GET /settings/data/export/
    Retorna JSON com todos os dados do usuário — direito de portabilidade LGPD.
    """
    user = request.user
    profile = user.profile

    try:
        page = Page.objects.get(user=user)
        blocks = list(
            Block.objects.filter(page=page).values(
                'title', 'url', 'block_type', 'is_active', 'order', 'clicks', 'created_at'
            )
        )
        # Analytics agregados (não raw — conformidade LGPD)
        aggregates = list(
            DailyAggregate.objects.filter(page=page).values(
                'date', 'total_views', 'total_clicks',
                'mobile_count', 'desktop_count', 'tablet_count', 'top_referer'
            )
        )
    except Page.DoesNotExist:
        blocks = []
        aggregates = []

    data = {
        'exportado_em': timezone.now().isoformat(),
        'usuario': {
            'email': user.email,
            'data_cadastro': user.date_joined.isoformat(),
        },
        'perfil': {
            'slug': profile.slug,
            'display_name': profile.display_name,
            'bio': profile.bio,
            'plano': profile.plan,
        },
        'links': [
            {
                **{k: (v.isoformat() if hasattr(v, 'isoformat') else v) for k, v in b.items()}
            }
            for b in blocks
        ],
        'analytics_agregados': [
            {
                **{k: (v.isoformat() if hasattr(v, 'isoformat') else v) for k, v in a.items()}
            }
            for a in aggregates
        ],
    }

    response = JsonResponse(data, json_dumps_params={'ensure_ascii': False, 'indent': 2})
    response['Content-Disposition'] = 'attachment; filename="meus_dados_lumebio.json"'
    return response


@login_required
def data_delete_confirm(request):
    """
    GET /settings/data/delete/
    Exibe a página de confirmação antes de deletar tudo.
    """
    return render(request, 'accounts/data_delete.html')


@login_required
@require_POST
def data_delete(request):
    """
    POST /settings/data/delete/
    Deleta todos os dados do usuário — direito ao esquecimento LGPD.
    Exige campo 'confirmo' = 'DELETAR' no body.
    """
    confirmacao = request.POST.get('confirmo', '').strip()

    if confirmacao != 'DELETAR':
        return render(request, 'accounts/data_delete.html', {
            'erro': 'Digite DELETAR exatamente para confirmar.'
        })

    user = request.user

    # Deleta dados em cascata
    try:
        page = Page.objects.get(user=user)
        # Analytics raw
        PageView.objects.filter(page=page).delete()
        LinkClick.objects.filter(block__page=page).delete()
        DailyAggregate.objects.filter(page=page).delete()
        # Página e blocos (cascade apaga blocos automaticamente)
        page.delete()
    except Page.DoesNotExist:
        pass

    # Deleta perfil e usuário
    profile = user.profile
    if profile.avatar:
        profile.avatar.delete(save=False)
    profile.delete()

    logout(request)
    user.delete()

    return redirect('/?conta_deletada=1')