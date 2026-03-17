"""
Testes de integração — BK-25, BK-26, BK-28
BK-25: public_page e block_redirect (com/sem consent)
BK-26: block_create com limite de plano Free
BK-28: tarefas Celery aggregate_daily_stats e purge_old_analytics
"""
import pytest
from datetime import date, timedelta
from django.utils import timezone

from apps.analytics.models import DailyAggregate, PageView
from apps.pages.models import Block, LinkClick
# ── imports adicionais no topo do arquivo ──
from unittest.mock import patch
from apps.analytics.tasks import record_page_view as _record_page_view_fn


class TestBK25PublicPage:

    def test_public_page_registra_pageview_sem_consentimento(self, client, user, page, db):
        page.is_published = True
        page.save()

        with patch('apps.pages.views.record_page_view.delay',
                   side_effect=lambda **kw: _record_page_view_fn(**kw)):
            client.get(f'/{user.profile.slug}/')

        assert PageView.objects.filter(page=page).count() == 1

    def test_public_page_registra_pageview_com_consentimento(self, client, user, page, db):
        page.is_published = True
        page.save()

        client.cookies['biolink_consent'] = 'accepted'
        with patch('apps.pages.views.record_page_view.delay',
                   side_effect=lambda **kw: _record_page_view_fn(**kw)):
            client.get(f'/{user.profile.slug}/')

        assert PageView.objects.filter(page=page).count() == 1

    def test_public_page_registra_pageview_com_consentimento_recusado(self, client, user, page, db):
        page.is_published = True
        page.save()

        client.cookies['biolink_consent'] = 'refused'
        with patch('apps.pages.views.record_page_view.delay',
                   side_effect=lambda **kw: _record_page_view_fn(**kw)):
            client.get(f'/{user.profile.slug}/')

        assert PageView.objects.filter(page=page).count() == 1


    def test_url_invalida_nao_cria_bloco(self, client, user_free, page_free):
        """BlockForm deve rejeitar URL com scheme inválido."""
        client.force_login(user_free)

        client.post('/dashboard/blocks/create/', {
            'block_type': 'link', 'title': 'Inválido',
            'url': 'javascript:alert(1)',  # scheme não permitido pelo URLValidator
            'description': '', 'icon': '',
        })
        assert Block.objects.filter(page=page_free).count() == 0

class TestBK25BlockRedirect:

    def test_redirect_sem_consent_nao_cria_linkclick(self, client, block, page):
        page.is_published = True
        page.save()

        client.get(f'/r/{block.id}/')
        assert LinkClick.objects.filter(block=block).count() == 0

    def test_redirect_com_consent_cria_linkclick(self, client, block, page):
        page.is_published = True
        page.save()

        client.cookies['biolink_consent'] = 'accepted'
        client.get(f'/r/{block.id}/')
        assert LinkClick.objects.filter(block=block).count() == 1

    def test_redirect_com_consent_recusado_nao_cria_linkclick(self, client, block, page):
        page.is_published = True
        page.save()

        client.cookies['biolink_consent'] = 'refused'
        client.get(f'/r/{block.id}/')
        assert LinkClick.objects.filter(block=block).count() == 0

    def test_redirect_aponta_para_url_correta(self, client, block, page):
        page.is_published = True
        page.save()

        response = client.get(f'/r/{block.id}/')
        assert response.status_code == 302
        assert response['Location'] == block.url

    def test_redirect_com_consent_incrementa_clicks(self, client, block, page):
        page.is_published = True
        page.save()

        client.cookies['biolink_consent'] = 'accepted'
        client.get(f'/r/{block.id}/')

        block.refresh_from_db()
        assert block.clicks == 1

    def test_redirect_sem_consent_nao_incrementa_clicks(self, client, block, page):
        page.is_published = True
        page.save()

        client.get(f'/r/{block.id}/')

        block.refresh_from_db()
        assert block.clicks == 0

    def test_redirect_linkclick_tem_device_type(self, client, block, page):
        """LinkClick criado deve ter device_type preenchido."""
        page.is_published = True
        page.save()

        client.cookies['biolink_consent'] = 'accepted'
        client.get(f'/r/{block.id}/', HTTP_USER_AGENT='Mozilla/5.0 (iPhone; CPU)')

        click = LinkClick.objects.get(block=block)
        assert click.device_type == 'mobile'

    def test_redirect_bloco_inativo_retorna_404(self, client, page, block):
        page.is_published = True
        page.save()
        block.is_active = False
        block.save()

        response = client.get(f'/r/{block.id}/')
        assert response.status_code == 404


# ─── BK-26: block_create com limite de plano ─────────────────────────────────

class TestBK26BlockCreateLimit:

    def test_free_cria_primeiro_bloco(self, client, user_free, page_free):
        client.force_login(user_free)
        response = client.post('/dashboard/blocks/create/', {
            'block_type': 'link',
            'title': 'Meu Link',
            'url': 'https://example.com',
            'description': '',
            'icon': '',
        })
        assert response.status_code == 302
        assert Block.objects.filter(page=page_free).count() == 1

    def test_free_bloqueado_no_limite(self, client, user_free, page_free, plan_free):
        for i in range(plan_free.max_links):
            Block.objects.create(
                page=page_free, title=f'Link {i}',
                url=f'https://example.com/{i}', block_type='link', order=i,
            )
        client.force_login(user_free)

        client.post('/dashboard/blocks/create/', {
            'block_type': 'link', 'title': 'Extra',
            'url': 'https://example.com/extra', 'description': '', 'icon': '',
        })
        assert Block.objects.filter(page=page_free).count() == plan_free.max_links

    def test_free_bloqueado_exibe_mensagem_de_erro(self, client, user_free, page_free, plan_free):
        for i in range(plan_free.max_links):
            Block.objects.create(
                page=page_free, title=f'Link {i}',
                url=f'https://example.com/{i}', block_type='link', order=i,
            )
        client.force_login(user_free)

        response = client.post('/dashboard/blocks/create/', {
            'block_type': 'link', 'title': 'Extra',
            'url': 'https://example.com/extra', 'description': '', 'icon': '',
        }, follow=True)

        msgs = [str(m) for m in response.context['messages']]
        assert any('limite' in m.lower() for m in msgs)

    def test_pro_cria_alem_do_limite_free(self, client, user_pro, page_pro):
        for i in range(6):
            Block.objects.create(
                page=page_pro, title=f'Link {i}',
                url=f'https://example.com/{i}', block_type='link', order=i,
            )
        client.force_login(user_pro)

        response = client.post('/dashboard/blocks/create/', {
            'block_type': 'link', 'title': 'Link 7',
            'url': 'https://example.com/7', 'description': '', 'icon': '',
        })
        assert response.status_code == 302
        assert Block.objects.filter(page=page_pro).count() == 7

    def test_url_invalida_nao_cria_bloco(self, client, user_free, page_free):
        """BlockForm deve rejeitar URLs com formato inválido."""
        client.force_login(user_free)

        client.post('/dashboard/blocks/create/', {
            'block_type': 'link', 'title': 'Inválido',
            'url': 'não é uma url válida',
            'description': '', 'icon': '',
        })
        assert Block.objects.filter(page=page_free).count() == 0


# ─── BK-28: Tarefas Celery ────────────────────────────────────────────────────

class TestBK28AggregateDailyStats:

    def test_aggregate_cria_registro_para_pagina(self, db, page):
        from apps.analytics.tasks import aggregate_daily_stats

        target = date.today()
        PageView.objects.create(
            page=page, ip_anon='1.2.3.0',
            device_type='mobile', referer_domain='instagram.com',
        )

        aggregate_daily_stats(page_id=page.id, target_date=str(target))

        agg = DailyAggregate.objects.get(page=page, date=target)
        assert agg.total_views == 1
        assert agg.mobile_count == 1

    def test_aggregate_contabiliza_cliques(self, db, page, block):
        from apps.analytics.tasks import aggregate_daily_stats

        target = date.today()
        LinkClick.objects.create(block=block, ip_address='', referer='')

        aggregate_daily_stats(page_id=page.id, target_date=str(target))

        agg = DailyAggregate.objects.get(page=page, date=target)
        assert agg.total_clicks == 1

    def test_aggregate_idempotente(self, db, page):
        from apps.analytics.tasks import aggregate_daily_stats

        target = date.today()
        aggregate_daily_stats(page_id=page.id, target_date=str(target))
        aggregate_daily_stats(page_id=page.id, target_date=str(target))

        assert DailyAggregate.objects.filter(page=page, date=target).count() == 1

    def test_aggregate_page_inexistente_retorna_mensagem(self, db):
        from apps.analytics.tasks import aggregate_daily_stats

        result = aggregate_daily_stats(page_id=99999, target_date='2026-01-01')
        assert result == 'Nenhuma página encontrada.'

    def test_aggregate_contabiliza_por_dispositivo(self, db, page):
        from apps.analytics.tasks import aggregate_daily_stats

        target = date.today()
        PageView.objects.create(page=page, ip_anon='1.0.0.0', device_type='mobile', referer_domain='')
        PageView.objects.create(page=page, ip_anon='2.0.0.0', device_type='desktop', referer_domain='')
        PageView.objects.create(page=page, ip_anon='3.0.0.0', device_type='tablet', referer_domain='')

        aggregate_daily_stats(page_id=page.id, target_date=str(target))

        agg = DailyAggregate.objects.get(page=page, date=target)
        assert agg.mobile_count == 1
        assert agg.desktop_count == 1
        assert agg.tablet_count == 1


class TestBK28PurgeOldAnalytics:

    def test_purge_remove_views_antigas(self, db, page):
        from apps.analytics.tasks import purge_old_analytics

        old_date = timezone.now() - timedelta(days=366)
        pv = PageView.objects.create(
            page=page, ip_anon='1.0.0.0',
            device_type='desktop', referer_domain='',
        )
        PageView.objects.filter(pk=pv.pk).update(viewed_at=old_date)

        purge_old_analytics()
        assert PageView.objects.filter(pk=pv.pk).count() == 0

    def test_purge_mantem_views_recentes(self, db, page):
        from apps.analytics.tasks import purge_old_analytics

        PageView.objects.create(
            page=page, ip_anon='1.0.0.0',
            device_type='desktop', referer_domain='',
        )

        purge_old_analytics()
        assert PageView.objects.filter(page=page).count() == 1

    def test_purge_remove_clicks_antigos(self, db, block):
        from apps.analytics.tasks import purge_old_analytics

        old_date = timezone.now() - timedelta(days=366)
        click = LinkClick.objects.create(block=block, ip_address='', referer='')
        LinkClick.objects.filter(pk=click.pk).update(clicked_at=old_date)

        purge_old_analytics()
        assert LinkClick.objects.filter(pk=click.pk).count() == 0

    def test_purge_retorna_mensagem_com_contagem(self, db, page):
        from apps.analytics.tasks import purge_old_analytics

        result = purge_old_analytics()
        assert 'Removidos:' in result
        assert 'views' in result
        assert 'cliques' in result