import json
import csv
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse
from django.db.models import Count
from django.db.models.functions import TruncDate
from django.utils import timezone
from datetime import timedelta

from apps.pages.models import Page, LinkClick
from apps.analytics.models import PageView


def get_period(request):
    """Retorna (days, label) conforme query param ?period="""
    period = request.GET.get('period', '30')
    options = {'7': 7, '30': 30, '90': 90}
    days = options.get(period, 30)
    return days, period


@login_required
def analytics(request):
    page = get_object_or_404(Page, user=request.user)
    blocks = page.blocks.all().order_by('order')
    days, period = get_period(request)

    today = timezone.localdate()
    since = timezone.now() - timedelta(days=days)
    since_7 = timezone.now() - timedelta(days=7)

    # ── KPIs ─────────────────────────────────────────────────────────────────
    clicks_today = LinkClick.objects.filter(
        block__page=page, clicked_at__date=today
    ).count()

    clicks_7d = LinkClick.objects.filter(
        block__page=page, clicked_at__gte=since_7
    ).count()

    clicks_period = LinkClick.objects.filter(
        block__page=page, clicked_at__gte=since
    ).count()

    views_period = PageView.objects.filter(
        page=page, viewed_at__gte=since
    ).count()

    conversion_rate = round((clicks_period / views_period * 100), 1) if views_period > 0 else 0

    # ── Ranking de links ──────────────────────────────────────────────────────
    block_stats = list(
        blocks.annotate(total_clicks=Count('link_clicks'))
              .values('id', 'title', 'url', 'block_type', 'clicks')
              .order_by('-clicks')
    )

    # ── Dados para gráfico de linha ───────────────────────────────────────────
    clicks_by_day = {
        str(r['date']): r['total']
        for r in LinkClick.objects
            .filter(block__page=page, clicked_at__gte=since)
            .annotate(date=TruncDate('clicked_at'))
            .values('date')
            .annotate(total=Count('id'))
    }

    views_by_day = {
        str(r['date']): r['total']
        for r in PageView.objects
            .filter(page=page, viewed_at__gte=since)
            .annotate(date=TruncDate('viewed_at'))
            .values('date')
            .annotate(total=Count('id'))
    }

    labels, clicks_data, views_data = [], [], []
    for i in range(days):
        d = str(today - timedelta(days=days - 1 - i))
        labels.append(d)
        clicks_data.append(clicks_by_day.get(d, 0))
        views_data.append(views_by_day.get(d, 0))

    # ── Dispositivos ──────────────────────────────────────────────────────────
    device_stats = list(
        PageView.objects
        .filter(page=page, viewed_at__gte=since)
        .values('device_type')
        .annotate(total=Count('id'))
        .order_by('-total')
    )
    device_labels = [d['device_type'].capitalize() for d in device_stats]
    device_data   = [d['total'] for d in device_stats]

    # ── Top origens ───────────────────────────────────────────────────────────
    top_referers = list(
        PageView.objects
        .filter(page=page, viewed_at__gte=since)
        .exclude(referer_domain='')
        .values('referer_domain')
        .annotate(total=Count('id'))
        .order_by('-total')[:5]
    )

    return render(request, 'analytics/index.html', {
        'page': page,
        'profile': request.user.profile,
        # período
        'period': period,
        'days': days,
        # KPIs
        'clicks_today':    clicks_today,
        'clicks_7d':       clicks_7d,
        'clicks_period':   clicks_period,
        'views_period':    views_period,
        'conversion_rate': conversion_rate,
        'active_blocks':   blocks.filter(is_active=True).count(),
        # tabela
        'block_stats':     block_stats,
        # Chart.js linha
        'chart_labels':    json.dumps(labels),
        'chart_clicks':    json.dumps(clicks_data),
        'chart_views':     json.dumps(views_data),
        # Chart.js pizza
        'device_labels':   json.dumps(device_labels),
        'device_data':     json.dumps(device_data),
        # origens
        'top_referers':    top_referers,
    })


@login_required
def export_csv(request):
    """Exporta cliques do período como CSV para download."""
    page = get_object_or_404(Page, user=request.user)
    days, period = get_period(request)
    since = timezone.now() - timedelta(days=days)

    clicks = (
        LinkClick.objects
        .filter(block__page=page, clicked_at__gte=since)
        .select_related('block')
        .order_by('-clicked_at')
    )

    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = (
        f'attachment; filename="analytics_{page.title}_{period}d.csv"'
    )
    response.write('\ufeff')

    writer = csv.writer(response)
    writer.writerow(['Data/Hora', 'Link', 'Destino', 'Dispositivo', 'Origem'])

    for click in clicks:
        writer.writerow([
            click.clicked_at.astimezone(
                timezone.get_current_timezone()
            ).strftime('%d/%m/%Y %H:%M'),
            click.block.title,
            click.block.url,
            click.device_type.capitalize(),
            click.referer or 'Acesso direto',
        ])

    return response