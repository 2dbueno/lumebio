import logging
from datetime import date, timedelta
from celery import shared_task
from django.db.models import Count
from django.utils import timezone
from apps.analytics.models import DailyAggregate, PageView
from apps.analytics.utils import anonymize_ip, extract_domain, parse_device
from apps.pages.models import LinkClick, Page

logger = logging.getLogger(__name__)


@shared_task
def record_page_view(page_id: int, ip: str, user_agent: str, referer: str):
    """
    Registra uma PageView de forma assíncrona para não travar a request.
    """
    try:
        page = Page.objects.get(id=page_id)
        PageView.objects.create(
            page=page,
            ip_anon=anonymize_ip(ip),
            device_type=parse_device(user_agent),
            referer_domain=extract_domain(referer),
        )
    except Page.DoesNotExist:
        pass


@shared_task
def aggregate_daily_stats(page_id: int = None, target_date: str = None):
    """
    Consolida PageViews e LinkClicks de um dia em DailyAggregate.

    Celery Beat (automático, sem argumentos):
        → roda para TODAS as páginas publicadas

    Manual/debug (com argumentos):
        aggregate_daily_stats(page_id=2, target_date='2026-03-13')
        → roda só para aquela página naquele dia
    """
    if target_date:
        d = date.fromisoformat(target_date)
    else:
        d = timezone.localdate() - timedelta(days=1)

    pages = (
        Page.objects.filter(id=page_id)
        if page_id
        else Page.objects.filter(is_published=True)
    )

    if not pages.exists():
        return 'Nenhuma página encontrada.'

    resultados = []
    for page in pages:
        views  = PageView.objects.filter(page=page, viewed_at__date=d)
        clicks = LinkClick.objects.filter(block__page=page, clicked_at__date=d)

        # Armazena contagens para reutilizar no log — evita queries duplicadas
        total_views  = views.count()
        total_clicks = clicks.count()

        device_map = {
            item['device_type']: item['total']
            for item in views.values('device_type').annotate(total=Count('id'))
        }

        top_ref = (
            views
            .exclude(referer_domain='')
            .values('referer_domain')
            .annotate(total=Count('id'))
            .order_by('-total')
            .first()
        )

        DailyAggregate.objects.update_or_create(
            page=page,
            date=d,
            defaults={
                'total_views':   total_views,
                'total_clicks':  total_clicks,
                'mobile_count':  device_map.get('mobile', 0),
                'desktop_count': device_map.get('desktop', 0),
                'tablet_count':  device_map.get('tablet', 0),
                'top_referer':   top_ref['referer_domain'] if top_ref else '',
            },
        )
        resultados.append(
            f'Página {page.id} ({page.title}): {total_views} views, {total_clicks} cliques'
        )

    return f'Agregado {d}: ' + ' | '.join(resultados)


@shared_task
def purge_old_analytics():
    """
    Deleta registros raw com mais de 12 meses (conformidade LGPD).
    Roda no dia 1 de cada mês às 03:00 via Celery Beat.
    """
    cutoff = timezone.now() - timedelta(days=365)
    deleted_views, _  = PageView.objects.filter(viewed_at__lt=cutoff).delete()
    deleted_clicks, _ = LinkClick.objects.filter(clicked_at__lt=cutoff).delete()
    return f'Removidos: {deleted_views} views e {deleted_clicks} cliques antigos.'