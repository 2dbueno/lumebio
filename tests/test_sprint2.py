"""
Testes do Sprint 2 — BK-07 e BK-08
Cobrem enforcement de limite de blocos por plano e feedback no dashboard.
"""
import pytest
from django.contrib.auth import get_user_model

from apps.accounts.models import Profile
from apps.billing.models import Plan
from apps.pages.models import Block, Page

User = get_user_model()


# ─── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture
def plan_free(db):
    plan, _ = Plan.objects.get_or_create(
        slug='free',
        defaults={'name': 'Free', 'price_monthly': 0, 'max_links': 5, 'is_active': True},
    )
    return plan


@pytest.fixture
def plan_pro(db):
    plan, _ = Plan.objects.get_or_create(
        slug='pro',
        defaults={'name': 'Pro', 'price_monthly': 29, 'max_links': None, 'is_active': True},
    )
    return plan


@pytest.fixture
def user_free(db, plan_free):
    user = User.objects.create_user(email='free@test.com', password='pass123')
    user.profile.plan = 'free'
    user.profile.save(update_fields=['plan'])
    return user


@pytest.fixture
def user_pro(db, plan_pro):
    user = User.objects.create_user(email='pro@test.com', password='pass123')
    user.profile.plan = 'pro'
    user.profile.save(update_fields=['plan'])
    return user


@pytest.fixture
def page_free(user_free):
    return Page.objects.get(user=user_free)


@pytest.fixture
def page_pro(user_pro):
    return Page.objects.get(user=user_pro)


def _create_blocks(page, count):
    """Cria `count` blocos na página sem passar pela view."""
    for i in range(count):
        Block.objects.create(
            page=page,
            title=f'Link {i + 1}',
            url=f'https://example.com/{i}',
            block_type='link',
            is_active=True,
            order=i,
        )


# ─── BK-07: Enforcement do limite de blocos ──────────────────────────────────

class TestBK07BlockLimit:

    def test_free_pode_criar_bloco_abaixo_do_limite(self, client, user_free, page_free, plan_free):
        """Usuário Free com 0 blocos deve conseguir criar."""
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

    def test_free_nao_pode_criar_bloco_no_limite(self, client, user_free, page_free, plan_free):
        """Usuário Free com 5 blocos não deve conseguir criar o 6º."""
        _create_blocks(page_free, 5)
        client.force_login(user_free)

        response = client.post('/dashboard/blocks/create/', {
            'block_type': 'link',
            'title': 'Bloco Extra',
            'url': 'https://example.com/extra',
            'description': '',
            'icon': '',
        })

        # Deve redirecionar de volta ao dashboard (não criar)
        assert response.status_code == 302
        assert Block.objects.filter(page=page_free).count() == 5

    def test_free_nao_pode_acessar_formulario_no_limite(self, client, user_free, page_free, plan_free):
        """GET em block_create com limite atingido deve redirecionar."""
        _create_blocks(page_free, 5)
        client.force_login(user_free)

        response = client.get('/dashboard/blocks/create/')
        assert response.status_code == 302

    def test_pro_pode_criar_alem_do_limite_free(self, client, user_pro, page_pro, plan_pro):
        """Usuário Pro deve criar blocos além de 5 sem restrição."""
        _create_blocks(page_pro, 5)
        client.force_login(user_pro)

        response = client.post('/dashboard/blocks/create/', {
            'block_type': 'link',
            'title': 'Bloco 6',
            'url': 'https://example.com/6',
            'description': '',
            'icon': '',
        })

        assert response.status_code == 302
        assert Block.objects.filter(page=page_pro).count() == 6

    def test_pro_sem_limite_pode_criar_muitos_blocos(self, client, user_pro, page_pro, plan_pro):
        """Usuário Pro não deve ter limite — cria 20 blocos sem problema."""
        _create_blocks(page_pro, 19)
        client.force_login(user_pro)

        response = client.post('/dashboard/blocks/create/', {
            'block_type': 'link',
            'title': 'Bloco 20',
            'url': 'https://example.com/20',
            'description': '',
            'icon': '',
        })

        assert response.status_code == 302
        assert Block.objects.filter(page=page_pro).count() == 20

    def test_limite_exato_bloqueia(self, client, user_free, page_free, plan_free):
        """Exatamente no limite (5/5) deve bloquear."""
        _create_blocks(page_free, plan_free.max_links)
        client.force_login(user_free)

        before = Block.objects.filter(page=page_free).count()
        client.post('/dashboard/blocks/create/', {
            'block_type': 'link',
            'title': 'Extra',
            'url': 'https://example.com',
            'description': '',
            'icon': '',
        })
        after = Block.objects.filter(page=page_free).count()

        assert before == after == plan_free.max_links


# ─── BK-08: Feedback visual no dashboard ─────────────────────────────────────

class TestBK08DashboardFeedback:

    def test_dashboard_mostra_contador_para_free(self, client, user_free, page_free, plan_free):
        """Dashboard deve exibir 'X de 5 blocos usados' para usuário Free."""
        _create_blocks(page_free, 3)
        client.force_login(user_free)

        response = client.get('/dashboard/')
        assert response.status_code == 200

        content = response.content.decode()
        assert '3 de 5 blocos usados' in content

    def test_dashboard_nao_mostra_contador_para_pro(self, client, user_pro, page_pro, plan_pro):
        """Dashboard não deve exibir contador de limite para usuário Pro (ilimitado)."""
        _create_blocks(page_pro, 3)
        client.force_login(user_pro)

        response = client.get('/dashboard/')
        content = response.content.decode()

        assert 'blocos usados' not in content

    def test_dashboard_mostra_botao_upgrade_no_limite(self, client, user_free, page_free, plan_free):
        """Com limite atingido, deve aparecer botão de upgrade no lugar de 'Novo bloco'."""
        _create_blocks(page_free, 5)
        client.force_login(user_free)

        response = client.get('/dashboard/')
        content = response.content.decode()

        assert 'Limite atingido' in content
        assert 'Novo bloco' not in content

    def test_dashboard_mostra_botao_criar_abaixo_do_limite(self, client, user_free, page_free, plan_free):
        """Abaixo do limite, deve aparecer botão 'Novo bloco' normalmente."""
        _create_blocks(page_free, 2)
        client.force_login(user_free)

        response = client.get('/dashboard/')
        content = response.content.decode()

        assert '+ Novo bloco' in content
        assert 'Limite atingido' not in content

    def test_dashboard_context_at_limit_true(self, client, user_free, page_free, plan_free):
        """Context 'at_limit' deve ser True quando no limite."""
        _create_blocks(page_free, 5)
        client.force_login(user_free)

        response = client.get('/dashboard/')
        assert response.context['at_limit'] is True

    def test_dashboard_context_at_limit_false(self, client, user_free, page_free, plan_free):
        """Context 'at_limit' deve ser False quando abaixo do limite."""
        _create_blocks(page_free, 2)
        client.force_login(user_free)

        response = client.get('/dashboard/')
        assert response.context['at_limit'] is False

    def test_dashboard_context_plan_limit_none_para_pro(self, client, user_pro, page_pro, plan_pro):
        """Context 'plan_limit' deve ser None para usuário Pro."""
        client.force_login(user_pro)

        response = client.get('/dashboard/')
        assert response.context['plan_limit'] is None

    def test_mensagem_erro_ao_tentar_criar_alem_do_limite(self, client, user_free, page_free, plan_free):
        """Deve exibir mensagem de erro ao tentar criar bloco além do limite."""
        _create_blocks(page_free, 5)
        client.force_login(user_free)

        # Segue o redirect para capturar as messages
        response = client.post('/dashboard/blocks/create/', {
            'block_type': 'link',
            'title': 'Extra',
            'url': 'https://example.com',
            'description': '',
            'icon': '',
        }, follow=True)

        messages = [str(m) for m in response.context['messages']]
        assert any('limite' in m.lower() for m in messages)