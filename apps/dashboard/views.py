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
    return render(request, 'dashboard/block_form.html', {'action': 'Criar'})


@login_required
def block_edit(request, block_id):
    page = get_object_or_404(Page, user=request.user)
    block = get_object_or_404(Block, id=block_id, page=page)
    if request.method == 'POST':
        block.block_type = request.POST.get('block_type', block.block_type)
        block.title = request.POST.get('title', block.title)
        block.url = request.POST.get('url', block.url)
        block.description = request.POST.get('description', block.description)
        block.icon = request.POST.get('icon', block.icon)
        block.is_active = request.POST.get('is_active') == 'on'
        block.save()
        messages.success(request, 'Bloco atualizado!')
        return redirect('dashboard')
    return render(request, 'dashboard/block_form.html', {'block': block, 'action': 'Editar'})


@login_required
def block_delete(request, block_id):
    page = get_object_or_404(Page, user=request.user)
    block = get_object_or_404(Block, id=block_id, page=page)
    if request.method == 'POST':
        block.delete()
        messages.success(request, 'Bloco removido!')
    return redirect('dashboard')


@login_required
def block_toggle(request, block_id):
    page = get_object_or_404(Page, user=request.user)
    block = get_object_or_404(Block, id=block_id, page=page)
    block.is_active = not block.is_active
    block.save(update_fields=['is_active'])
    return redirect('dashboard')

@login_required
@require_POST
def block_reorder(request):
    page = get_object_or_404(Page, user=request.user)
    try:
        data = json.loads(request.body)
        order = data.get('order', [])  # lista de IDs na nova ordem
        for index, block_id in enumerate(order):
            page.blocks.filter(id=block_id).update(order=index)
        return JsonResponse({'status': 'ok'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)