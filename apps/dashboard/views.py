import json
import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.pages.models import Block, Page

logger = logging.getLogger(__name__)


def _get_block_limit(profile):
    """
    Retorna o limite de blocos do plano do usuário.
    Retorna None se o plano for ilimitado (Pro).
    Usa fallback de 5 se o plano não existir no banco.
    """
    from apps.billing.models import Plan
    try:
        plan = Plan.objects.get(slug=profile.plan)
        return plan.max_links  # None = ilimitado
    except Plan.DoesNotExist:
        logger.warning(f'Plano "{profile.plan}" não encontrado no banco para {profile.slug}. Usando fallback=5.')
        return 5


@login_required
def dashboard(request):
    page = get_object_or_404(Page, user=request.user)
    blocks = page.blocks.all().order_by('order')
    total_clicks = sum(b.clicks for b in blocks)
    profile = request.user.profile

    plan_limit = _get_block_limit(profile)
    block_count = len(blocks)  # já está em memória — não faz nova query
    at_limit = plan_limit is not None and block_count >= plan_limit

    return render(request, 'dashboard/index.html', {
        'user': request.user,
        'profile': profile,
        'page': page,
        'blocks': blocks,
        'total_clicks': total_clicks,
        'plan_limit': plan_limit,
        'block_count': block_count,
        'at_limit': at_limit,
    })


@login_required
def page_edit(request):
    page = get_object_or_404(Page, user=request.user)
    profile = request.user.profile

    if request.method == 'POST':
        requested_theme = request.POST.get('theme', page.theme)

        # bloqueia tema Pro para usuário Free
        if requested_theme in Page.PRO_THEMES and not profile.is_pro:
            messages.error(
                request,
                'Este tema é exclusivo do plano Pro. Faça upgrade para utilizá-lo.'
            )
            return redirect('page_edit')

        page.title = request.POST.get('title', page.title)
        page.bio = request.POST.get('bio', page.bio)
        page.theme = requested_theme
        page.is_published = request.POST.get('is_published') == 'on'
        page.save()
        messages.success(request, 'Página atualizada!')
        return redirect('dashboard')

    return render(request, 'dashboard/page_edit.html', {
        'page': page,
        'profile': profile,
    })

@login_required
def block_create(request):
    page = get_object_or_404(Page, user=request.user)
    profile = request.user.profile

    # BK-07: verifica limite do plano antes de qualquer coisa
    plan_limit = _get_block_limit(profile)
    current_count = page.blocks.count()

    if plan_limit is not None and current_count >= plan_limit:
        messages.error(
            request,
            f'Você atingiu o limite de {plan_limit} blocos do plano Free. '
            f'Faça upgrade para adicionar links ilimitados.'
        )
        return redirect('dashboard')

    if request.method == 'POST':
        Block.objects.create(
            page=page,
            block_type=request.POST.get('block_type', 'link'),
            title=request.POST.get('title', ''),
            url=request.POST.get('url', ''),
            description=request.POST.get('description', ''),
            icon=request.POST.get('icon', ''),
            order=current_count,
        )
        messages.success(request, 'Bloco criado!')
        return redirect('dashboard')

    return render(request, 'dashboard/block_form.html', {'action': 'Criar', 'blk': None})


@login_required
def block_edit(request, block_id):
    page = get_object_or_404(Page, user=request.user)
    blk = get_object_or_404(Block, id=block_id, page=page)
    if request.method == 'POST':
        blk.block_type  = request.POST.get('block_type', blk.block_type)
        blk.title       = request.POST.get('title', blk.title)
        blk.url         = request.POST.get('url', blk.url)
        blk.description = request.POST.get('description', blk.description)
        blk.icon        = request.POST.get('icon', blk.icon)
        blk.is_active   = request.POST.get('is_active') == 'on'
        blk.save()
        messages.success(request, 'Bloco atualizado!')
        return redirect('dashboard')
    return render(request, 'dashboard/block_form.html', {'blk': blk, 'action': 'Editar'})


@login_required
def block_delete(request, block_id):
    page = get_object_or_404(Page, user=request.user)
    blk = get_object_or_404(Block, id=block_id, page=page)
    if request.method == 'POST':
        blk.delete()
        messages.success(request, 'Bloco removido!')
    return redirect('dashboard')


@login_required
def block_toggle(request, block_id):
    page = get_object_or_404(Page, user=request.user)
    blk = get_object_or_404(Block, id=block_id, page=page)
    blk.is_active = not blk.is_active
    blk.save(update_fields=['is_active'])
    return redirect('dashboard')


@login_required
@require_POST
def block_reorder(request):
    page = get_object_or_404(Page, user=request.user)
    try:
        data = json.loads(request.body)
        order = data.get('order', [])
        for index, block_id in enumerate(order):
            page.blocks.filter(id=block_id).update(order=index)
        return JsonResponse({'status': 'ok'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)