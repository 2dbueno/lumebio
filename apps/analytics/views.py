from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404
from django.db.models import Count
from django.db.models.functions import TruncDate
from django.utils import timezone
from datetime import timedelta

from apps.pages.models import Page, Block, LinkClick


@login_required
def analytics(request):
    page = get_object_or_404(Page, user=request.user)
    blocks = page.blocks.all().order_by('order')

    # Cliques por bloco
    block_stats = blocks.annotate(
        total_clicks=Count('link_clicks')
    ).values('id', 'title', 'block_type', 'clicks')

    # Cliques por dia (últimos 30 dias)
    since = timezone.now() - timedelta(days=30)
    clicks_by_day = (
        LinkClick.objects
        .filter(block__page=page, clicked_at__gte=since)
        .annotate(date=TruncDate('clicked_at'))
        .values('date')
        .annotate(total=Count('id'))
        .order_by('date')
    )

    total_clicks = sum(b['clicks'] for b in block_stats)
    active_blocks = blocks.filter(is_active=True).count()
    clicks_last_30 = sum(d['total'] for d in clicks_by_day)

    return render(request, 'analytics/index.html', {
        'page': page,
        'profile': request.user.profile,
        'block_stats': block_stats,
        'clicks_by_day': list(clicks_by_day),
        'total_clicks': total_clicks,
        'active_blocks': active_blocks,
        'clicks_last_30': clicks_last_30,
    })
