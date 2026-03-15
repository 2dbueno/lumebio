from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from apps.pages.models import Page, Block
import json
from django.http import JsonResponse
from django.views.decorators.http import require_POST

@login_required
def dashboard(request):
    page = get_object_or_404(Page, user=request.user)
    blocks = page.blocks.all().order_by('order')
    total_clicks = sum(b.clicks for b in blocks)
    return render(request, 'dashboard/index.html', {
        'user': request.user,
        'profile': request.user.profile,
        'page': page,
        'blocks': blocks,
        'total_clicks': total_clicks,
    })

@login_required
def page_edit(request):
    page = get_object_or_404(Page, user=request.user)
    if request.method == 'POST':
        page.title = request.POST.get('title', page.title)
        page.bio = request.POST.get('bio', page.bio)
        page.theme = request.POST.get('theme', page.theme)
        page.is_published = request.POST.get('is_published') == 'on'
        page.save()
        messages.success(request, 'Página atualizada!')
        return redirect('dashboard')
    return render(request, 'dashboard/page_edit.html', {'page': page})


@login_required
def block_create(request):
    page = get_object_or_404(Page, user=request.user)
    if request.method == 'POST':
        Block.objects.create(
            page=page,
            block_type=request.POST.get('block_type', 'link'),
            title=request.POST.get('title', ''),
            url=request.POST.get('url', ''),
            description=request.POST.get('description', ''),
            icon=request.POST.get('icon', ''),
            order=page.blocks.count(),
        )
        messages.success(request, 'Bloco criado!')
        return redirect('dashboard')
    # 'blk': None deixa claro ao template que é criação (sem dados)
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
    # variável renomeada para 'blk' — 'block' é palavra reservada nos templates Django
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