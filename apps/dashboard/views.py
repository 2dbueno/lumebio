import json
import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.pages.models import Block, Page
from apps.dashboard.forms import BlockForm, PageEditForm

logger = logging.getLogger(__name__)


def _get_block_limit(profile):
    from apps.billing.models import Plan
    try:
        plan = Plan.objects.get(slug=profile.plan)
        return plan.max_links
    except Plan.DoesNotExist:
        logger.warning(
            f'Plano "{profile.plan}" não encontrado para {profile.slug}. Usando fallback=5.'
        )
        return 5


@login_required
def dashboard(request):
    page = get_object_or_404(Page.objects.select_related('user'), user=request.user)
    blocks = page.blocks.prefetch_related('link_clicks').order_by('order')
    profile = request.user.profile
    plan_limit = _get_block_limit(profile)
    block_count = blocks.count()
    at_limit = plan_limit is not None and block_count >= plan_limit
    total_clicks = sum(b.clicks for b in blocks)

    return render(request, 'dashboard/index.html', {
        'user':         request.user,
        'profile':      profile,
        'page':         page,
        'blocks':       blocks,
        'total_clicks': total_clicks,
        'plan_limit':   plan_limit,
        'block_count':  block_count,
        'at_limit':     at_limit,
    })


@login_required
def page_edit(request):
    page    = get_object_or_404(Page, user=request.user)
    profile = request.user.profile

    if request.method == 'POST':
        form = PageEditForm(request.POST, instance=page, profile=profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Página atualizada!')
            return redirect('dashboard:dashboard')
        for field_errors in form.errors.values():
            for error in field_errors:
                messages.error(request, error)
    else:
        form = PageEditForm(instance=page, profile=profile)

    return render(request, 'dashboard/page_edit.html', {
        'form':    form,
        'page':    page,
        'profile': profile,
    })


@login_required
def block_create(request):
    page    = get_object_or_404(Page, user=request.user)
    profile = request.user.profile

    plan_limit    = _get_block_limit(profile)
    current_count = page.blocks.count()

    if plan_limit is not None and current_count >= plan_limit:
        messages.error(
            request,
            f'Você atingiu o limite de {plan_limit} blocos do plano Free. '
            f'Faça upgrade para adicionar links ilimitados.'
        )
        return redirect('dashboard:dashboard')

    if request.method == 'POST':
        form = BlockForm(request.POST)
        if form.is_valid():
            block = form.save(commit=False)
            block.page  = page
            block.order = current_count
            block.save()
            messages.success(request, 'Bloco criado!')
            return redirect('dashboard:dashboard')
    else:
        form = BlockForm()

    return render(request, 'dashboard/block_form.html', {
        'form':   form,
        'action': 'Criar',
        'blk':    None,
    })


@login_required
def block_edit(request, block_id):
    page = get_object_or_404(Page, user=request.user)
    blk  = get_object_or_404(Block, id=block_id, page=page)

    if request.method == 'POST':
        form = BlockForm(request.POST, instance=blk)
        if form.is_valid():
            form.save()
            messages.success(request, 'Bloco atualizado!')
            return redirect('dashboard:dashboard')
    else:
        form = BlockForm(instance=blk)

    return render(request, 'dashboard/block_form.html', {
        'form':   form,
        'blk':    blk,
        'action': 'Editar',
    })


@login_required
def block_delete(request, block_id):
    page = get_object_or_404(Page, user=request.user)
    blk  = get_object_or_404(Block, id=block_id, page=page)
    if request.method == 'POST':
        blk.delete()
        messages.success(request, 'Bloco removido!')
    return redirect('dashboard:dashboard')


@login_required
def block_toggle(request, block_id):
    page = get_object_or_404(Page, user=request.user)
    blk  = get_object_or_404(Block, id=block_id, page=page)
    blk.is_active = not blk.is_active
    blk.save(update_fields=['is_active'])
    return redirect('dashboard:dashboard')


@login_required
@require_POST
def block_reorder(request):
    page = get_object_or_404(Page, user=request.user)
    try:
        data  = json.loads(request.body)
        order = data.get('order', [])
        for index, block_id in enumerate(order):
            page.blocks.filter(id=block_id).update(order=index)
        return JsonResponse({'status': 'ok'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)