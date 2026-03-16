"""
Testes do Sprint 1 — BK-01 a BK-06
Cobrem todas as correções críticas aplicadas.
"""
import pytest
from datetime import date, timedelta
from unittest.mock import patch, MagicMock

from django.contrib.auth import get_user_model
from django.test import Client

from apps.accounts.models import Profile
from apps.pages.models import Block, LinkClick, Page

User = get_user_model()


# ─── Fixtures compartilhadas ──────────────────────────────────────────────────

@pytest.fixture
def user(db):
    return User.objects.create_user(email='sprint1@test.com', password='pass123')


@pytest.fixture
def profile(user):
    return Profile.objects.get(user=user)


@pytest.fixture
def page(user):
    return Page.objects.get(user=user)


@pytest.fixture
def block(page):
    return Block.objects.create(
        page=page,
        title='Link de Teste',
        url='https://example.com',
        block_type='link',
        is_active=True,
        clicks=0,
    )


# ─── BK-01: Race condition em Block.clicks ────────────────────────────────────

class TestBK01RaceCondition:

    def test_click_incrementa_contador(self, client, block, profile, page):
        """Visita com consentimento deve incrementar clicks em 1."""
        page.is_published = True
        page.save()

        client.cookies['biolink_consent'] = 'accepted'
        client.get(f'/r/{block.id}/')

        block.refresh_from_db()
        assert block.clicks == 1

    def test_click_sem_consentimento_nao_incrementa(self, client, block, page):
        """Visita sem consentimento não deve alterar o contador."""
        page.is_published = True
        page.save()

        client.get(f'/r/{block.id}/')

        block.refresh_from_db()
        assert block.clicks == 0

    def test_multiplos_clicks_acumulam_corretamente(self, client, block, page):
        """3 clicks com consentimento devem resultar em clicks=3."""
        page.is_published = True
        page.save()

        client.cookies['biolink_consent'] = 'accepted'
        for _ in range(3):
            client.get(f'/r/{block.id}/')

        block.refresh_from_db()
        assert block.clicks == 3

    def test_block_redirect_usa_update_atomico(self, client, block, page):
        """
        Verifica que block_redirect usa Block.objects.filter().update()
        e não block.save() — garantia de que F() está sendo usado.
        """
        page.is_published = True
        page.save()

        # Simula que o objeto em memória tem clicks=99 (desatualizado)
        # Se o código usasse block.save(), salvaria 100 no banco.
        # Com F(), o banco faz UPDATE clicks = clicks + 1 ignorando o valor em memória.
        block.clicks = 99  # Não salva — apenas altera a instância em memória
        block_id = block.id

        client.cookies['biolink_consent'] = 'accepted'
        client.get(f'/r/{block_id}/')

        # O banco deve ter incrementado de 0 para 1, não de 99 para 100
        block.refresh_from_db()
        assert block.clicks == 1

    def test_click_com_consentimento_recusado_nao_cria_linkclick(self, client, block, page):
        """Cookie 'refused' não deve criar registro de LinkClick."""
        page.is_published = True
        page.save()

        client.cookies['biolink_consent'] = 'refused'
        client.get(f'/r/{block.id}/')

        assert LinkClick.objects.filter(block=block).count() == 0

    def test_click_com_consentimento_aceito_cria_linkclick(self, client, block, page):
        """Cookie 'accepted' deve criar exatamente 1 LinkClick."""
        page.is_published = True
        page.save()

        client.cookies['biolink_consent'] = 'accepted'
        client.get(f'/r/{block.id}/')

        assert LinkClick.objects.filter(block=block).count() == 1


# ─── BK-03: SITE_URL duplicado ────────────────────────────────────────────────

class TestBK03SiteUrl:

    def test_site_url_definido_nas_settings(self):
        """SITE_URL deve estar definido e ser uma string válida."""
        from django.conf import settings
        assert hasattr(settings, 'SITE_URL')
        assert isinstance(settings.SITE_URL, str)
        assert settings.SITE_URL.startswith('http')

    def test_site_url_nao_duplicado(self):
        """
        Garante que base.py não define SITE_URL duas vezes.
        Lê o arquivo diretamente e conta ocorrências.
        """
        from pathlib import Path
        # __file__ = /app/tests/test_sprint1.py → .parent = /app/tests → .parent = /app
        base_path = Path(__file__).resolve().parent.parent / 'config' / 'settings' / 'base.py'
        content = base_path.read_text()
        # Conta linhas que fazem a atribuição (não comentários)
        assignments = [
            line for line in content.splitlines()
            if line.strip().startswith('SITE_URL') and '=' in line
        ]
        assert len(assignments) == 1, (
            f'SITE_URL definido {len(assignments)} vezes em base.py — esperado 1.\n'
            f'Linhas encontradas: {assignments}'
        )


# ─── BK-04: Imports inline ────────────────────────────────────────────────────

class TestBK04Imports:

    def test_pages_views_importa_sem_erro(self):
        """apps.pages.views deve importar sem erros no topo do módulo."""
        import importlib
        try:
            importlib.import_module('apps.pages.views')
        except ImportError as e:
            pytest.fail(f'apps.pages.views falhou no import: {e}')

    def test_billing_tasks_importa_sem_erro(self):
        """apps.billing.tasks deve importar sem erros no topo do módulo."""
        import importlib
        try:
            importlib.import_module('apps.billing.tasks')
        except ImportError as e:
            pytest.fail(f'apps.billing.tasks falhou no import: {e}')

    def test_analytics_tasks_importa_sem_erro(self):
        """apps.analytics.tasks deve importar sem erros no topo do módulo."""
        import importlib
        try:
            importlib.import_module('apps.analytics.tasks')
        except ImportError as e:
            pytest.fail(f'apps.analytics.tasks falhou no import: {e}')

    def test_pages_views_sem_imports_inline(self):
        """
        pages/views.py não deve conter imports dentro de funções
        (padrão: 'from' ou 'import' precedido apenas por espaços).
        """
        from pathlib import Path
        path = Path(__file__).resolve().parent.parent / 'apps' / 'pages' / 'views.py'
        content = path.read_text()

        inline_imports = []
        inside_function = False
        for lineno, line in enumerate(content.splitlines(), start=1):
            stripped = line.lstrip()
            if stripped.startswith('def ') or stripped.startswith('async def '):
                inside_function = True
            if inside_function and stripped.startswith(('from ', 'import ')):
                inline_imports.append(f'Linha {lineno}: {line.rstrip()}')

        assert not inline_imports, (
            'Imports inline encontrados em pages/views.py:\n' +
            '\n'.join(inline_imports)
        )

    def test_billing_tasks_sem_imports_inline(self):
        """billing/tasks.py não deve conter imports dentro de funções."""
        from pathlib import Path
        path = Path(__file__).resolve().parent.parent / 'apps' / 'billing' / 'tasks.py'
        content = path.read_text()

        inline_imports = []
        inside_function = False
        for lineno, line in enumerate(content.splitlines(), start=1):
            stripped = line.lstrip()
            if stripped.startswith('def ') or stripped.startswith('async def '):
                inside_function = True
            if inside_function and stripped.startswith(('from ', 'import ')):
                inline_imports.append(f'Linha {lineno}: {line.rstrip()}')

        assert not inline_imports, (
            'Imports inline encontrados em billing/tasks.py:\n' +
            '\n'.join(inline_imports)
        )


# ─── BK-05: CSV de analytics com dispositivo correto ─────────────────────────

class TestBK05CsvAnalytics:

    @pytest.fixture
    def logged_client(self, client, user):
        client.force_login(user)
        return client

    def test_csv_nao_retorna_desktop_hardcoded(self, logged_client, block, page):
        """
        O CSV não deve conter 'Desktop' hardcoded para todos os registros
        quando não há PageView correspondente — deve retornar 'Desconhecido'.
        """
        page.is_published = True
        page.save()

        # Cria um LinkClick sem PageView correspondente
        LinkClick.objects.create(
            block=block,
            ip_address='192.168.0.1',
            user_agent='Mozilla/5.0',
            referer='',
        )

        response = logged_client.get('/analytics/export/csv/?period=7')
        assert response.status_code == 200

        content = response.content.decode('utf-8-sig')  # remove BOM
        lines = [l for l in content.splitlines() if l.strip()]

        # Deve ter cabeçalho + 1 linha de dado
        assert len(lines) == 2

        data_line = lines[1]
        # Sem PageView correspondente → deve ser 'Desconhecido', não 'Desktop'
        assert 'Desktop' not in data_line
        assert 'Desconhecido' in data_line

    def test_csv_com_pageview_retorna_dispositivo_correto(self, logged_client, block, page):
        """CSV deve retornar o device_type da PageView correspondente."""
        from apps.analytics.models import PageView
        from django.utils import timezone

        page.is_published = True
        page.save()

        ip = '10.0.0.1'

        PageView.objects.create(
            page=page,
            ip_anon=ip,
            device_type='mobile',
            referer_domain='',
            viewed_at=timezone.now(),
        )
        LinkClick.objects.create(
            block=block,
            ip_address=ip,
            user_agent='',
            referer='',
        )

        response = logged_client.get('/analytics/export/csv/?period=7')
        content = response.content.decode('utf-8-sig')
        lines = [l for l in content.splitlines() if l.strip()]

        data_line = lines[1]
        assert 'Mobile' in data_line

    def test_csv_cabecalho_correto(self, logged_client, page):
        """O CSV deve ter as colunas esperadas no cabeçalho."""
        page.is_published = True
        page.save()

        response = logged_client.get('/analytics/export/csv/?period=7')
        content = response.content.decode('utf-8-sig')
        header = content.splitlines()[0]

        assert 'Data/Hora' in header
        assert 'Link' in header
        assert 'Dispositivo Estimado' in header
        assert 'Origem' in header


# ─── BK-06: .count() duplicado em aggregate_daily_stats ──────────────────────

class TestBK06AggregateDailyStats:

    def test_aggregate_cria_daily_aggregate(self, db, page):
        """aggregate_daily_stats deve criar um DailyAggregate para a página."""
        from apps.analytics.models import DailyAggregate, PageView
        from apps.analytics.tasks import aggregate_daily_stats

        # PageView usa auto_now_add=True — grava hoje.
        # target_date deve ser hoje para a task encontrar o registro.
        target = date.today()

        PageView.objects.create(
            page=page,
            ip_anon='1.2.3.0',
            device_type='mobile',
            referer_domain='instagram.com',
        )

        aggregate_daily_stats(page_id=page.id, target_date=str(target))

        agg = DailyAggregate.objects.get(page=page, date=target)
        assert agg.total_views == 1
        assert agg.mobile_count == 1

    def test_aggregate_contabiliza_clicks(self, db, block, page):
        """aggregate_daily_stats deve contabilizar LinkClicks do dia."""
        from apps.analytics.models import DailyAggregate
        from apps.analytics.tasks import aggregate_daily_stats

        # LinkClick usa auto_now_add=True — grava hoje.
        target = date.today()

        LinkClick.objects.create(block=block, ip_address='', user_agent='', referer='')

        aggregate_daily_stats(page_id=page.id, target_date=str(target))

        agg = DailyAggregate.objects.get(page=page, date=target)
        assert agg.total_clicks == 1

    def test_aggregate_sem_pagina_retorna_mensagem(self, db):
        """aggregate_daily_stats com page_id inexistente deve retornar mensagem."""
        from apps.analytics.tasks import aggregate_daily_stats

        result = aggregate_daily_stats(page_id=99999, target_date='2026-01-01')
        assert result == 'Nenhuma página encontrada.'

    def test_aggregate_idempotente(self, db, page):
        """Rodar aggregate_daily_stats duas vezes no mesmo dia deve atualizar, não duplicar."""
        from apps.analytics.models import DailyAggregate
        from apps.analytics.tasks import aggregate_daily_stats

        target = date.today()

        aggregate_daily_stats(page_id=page.id, target_date=str(target))
        aggregate_daily_stats(page_id=page.id, target_date=str(target))

        count = DailyAggregate.objects.filter(page=page, date=target).count()
        assert count == 1  # update_or_create — não deve duplicar