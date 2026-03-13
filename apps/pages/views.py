from django.shortcuts import render, get_object_or_404, redirect
from apps.accounts.models import Profile
from .models import Page, Block, LinkClick


def public_page(request, username):
    profile = get_object_or_404(Profile, slug=username)
    page = get_object_or_404(Page, user=profile.user, is_published=True)
    blocks = page.blocks.filter(is_active=True).order_by('order')
    return render(request, 'pages/public_page.html', {
        'page': page,
        'blocks': blocks,
        'profile': profile,
    })


def block_redirect(request, block_id):
    block = get_object_or_404(Block, id=block_id, is_active=True)
    LinkClick.objects.create(
        block=block,
        ip_address=request.META.get('REMOTE_ADDR'),
        user_agent=request.META.get('HTTP_USER_AGENT', ''),
        referer=request.META.get('HTTP_REFERER', ''),
    )
    block.clicks += 1
    block.save(update_fields=['clicks'])
    return redirect(block.url)
