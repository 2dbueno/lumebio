"""
Testes do Sprint 3 — BK-09
Cobrem o gate de temas Pro para usuários Free.
"""
import pytest
from django.contrib.auth import get_user_model

from apps.billing.models import Plan
from apps.pages.models import Page

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
    user = User.objects.create_user(email='free_theme@test.com', password='pass123')
    user.profile.plan = 'free'
    user.profile.save(update_fields=['plan'])
    return user


@pytest.fixture
def user_pro(db, plan_pro):
    user = User.objects.create_user(email='pro_theme@test.com', password='pass123')
    user.profile.plan = 'pro'
    user.profile.save(update_fields=['plan'])
    return user


@pytest.fixture
def page_free(user_free):
    return Page.objects.get(user=user_free)


@pytest.fixture
def page_pro(user_pro):
    return Page.objects.get(user=user_pro)


# ─── Helpers ─────────────────────────────────────────────────────────────────

FREE_THEMES = ['neon-dark', 'cyber-blue', 'aurora']
PRO_THEMES  = list(Page.PRO_THEMES)


def post_theme(client, theme):
    return client.post('/dashboard/page/edit/', {
        'title': 'Teste',
        'bio': '',
        'theme': theme,
        'is_published': 'on',
    })


# ─── Model ───────────────────────────────────────────────────────────────────

class TestBK09PageModel:

    def test_pro_themes_set_nao_vazio(self):
        """PRO_THEMES deve ter exatamente 10 temas."""
        assert len(Page.PRO_THEMES) == 10

    def test_free_themes_nao_estao_em_pro_themes(self):
        """Nenhum tema Free deve estar na lista Pro."""
        for t in FREE_THEMES:
            assert t not in Page.PRO_THEMES, f'{t} não deveria estar em PRO_THEMES'

    @pytest.mark.django_db
    def test_todos_pro_themes_tem_vars_definidas(self):
        """Cada tema Pro deve ter registro no banco com as chaves esperadas."""
        from apps.pages.models import Theme
        keys = {'bg', 'primary', 'accent', 'card_bg', 'card_border', 'text', 'subtext'}
        for slug in Page.PRO_THEMES:
            theme = Theme.objects.filter(slug=slug).first()
            assert theme is not None, f'Tema {slug} ausente no banco'
            assert keys == set(theme.as_vars().keys()), \
                f'Tema {slug} com chaves incorretas'

    def test_todos_pro_themes_estao_em_theme_choices(self):
        """Cada tema Pro deve estar registrado em THEME_CHOICES."""
        choice_slugs = {slug for slug, _ in Page.THEME_CHOICES}
        for slug in Page.PRO_THEMES:
            assert slug in choice_slugs, f'{slug} ausente em THEME_CHOICES'

    def test_get_theme_vars_retorna_fallback_para_tema_invalido(self, db, page_free):
        """get_theme_vars com tema inválido deve retornar neon-dark como fallback."""
        from apps.pages.models import Theme
        page_free.theme = 'tema-inexistente'
        fallback_vars = Theme.objects.get(slug='neon-dark').as_vars()
        vars = page_free.get_theme_vars()
        assert vars['bg'] == fallback_vars['bg']


# ─── Gate na view (Free) ──────────────────────────────────────────────────────

class TestBK09FreeUserGate:

    @pytest.mark.parametrize('theme', PRO_THEMES)
    def test_free_nao_pode_aplicar_tema_pro(self, client, user_free, page_free, theme):
        """Usuário Free não deve conseguir aplicar nenhum tema Pro via POST."""
        client.force_login(user_free)
        page_free.theme = 'neon-dark'
        page_free.save()

        post_theme(client, theme)

        page_free.refresh_from_db()
        assert page_free.theme == 'neon-dark', \
            f'Tema {theme} foi aplicado indevidamente para usuário Free'

    @pytest.mark.parametrize('theme', PRO_THEMES)
    def test_free_recebe_mensagem_de_erro_ao_tentar_tema_pro(self, client, user_free, page_free, theme):
        """Deve exibir mensagem de erro ao tentar aplicar tema Pro."""
        client.force_login(user_free)

        response = post_theme(client, theme)
        # Segue o redirect para capturar messages
        if response.status_code == 302:
            response = client.get(response['Location'])

        messages = [str(m) for m in response.context['messages']]
        assert any('pro' in m.lower() or 'upgrade' in m.lower() or 'exclusivo' in m.lower()
                   for m in messages), \
            f'Nenhuma mensagem de erro encontrada para tema {theme}'

    @pytest.mark.parametrize('theme', FREE_THEMES)
    def test_free_pode_aplicar_tema_free(self, client, user_free, page_free, theme):
        """Usuário Free deve conseguir aplicar qualquer tema Free."""
        client.force_login(user_free)

        response = post_theme(client, theme)
        assert response.status_code == 302

        page_free.refresh_from_db()
        assert page_free.theme == theme, \
            f'Tema Free {theme} não foi aplicado'

    def test_free_tema_pro_nao_altera_outros_campos(self, client, user_free, page_free):
        """Ao bloquear tema Pro, título e bio não devem ser alterados."""
        client.force_login(user_free)
        page_free.title = 'Título Original'
        page_free.bio = 'Bio original'
        page_free.theme = 'neon-dark'
        page_free.save()

        client.post('/dashboard/page/edit/', {
            'title': 'Novo Título',
            'bio': 'Nova bio',
            'theme': 'matrix',
            'is_published': 'on',
        })

        page_free.refresh_from_db()
        # Tema não mudou — e título/bio também não (POST foi rejeitado antes de salvar)
        assert page_free.theme == 'neon-dark'
        assert page_free.title == 'Título Original'


# ─── Gate na view (Pro) ───────────────────────────────────────────────────────

class TestBK09ProUserAccess:

    @pytest.mark.parametrize('theme', PRO_THEMES)
    def test_pro_pode_aplicar_qualquer_tema_pro(self, client, user_pro, page_pro, theme):
        """Usuário Pro deve conseguir aplicar qualquer tema Pro."""
        client.force_login(user_pro)

        response = post_theme(client, theme)
        assert response.status_code == 302

        page_pro.refresh_from_db()
        assert page_pro.theme == theme, \
            f'Tema Pro {theme} não foi aplicado para usuário Pro'

    @pytest.mark.parametrize('theme', FREE_THEMES)
    def test_pro_pode_aplicar_tema_free(self, client, user_pro, page_pro, theme):
        """Usuário Pro também deve poder usar temas Free."""
        client.force_login(user_pro)

        response = post_theme(client, theme)
        assert response.status_code == 302

        page_pro.refresh_from_db()
        assert page_pro.theme == theme


# ─── Template ────────────────────────────────────────────────────────────────

class TestBK09Template:

    def test_page_edit_exibe_temas_pro_com_cadeado_para_free(self, client, user_free, page_free):
        """Usuário Free deve ver o cadeado 🔒 nos temas Pro."""
        client.force_login(user_free)
        response = client.get('/dashboard/page/edit/')
        content = response.content.decode()

        assert '🔒' in content

    def test_page_edit_exibe_link_upgrade_para_free(self, client, user_free, page_free):
        """Usuário Free deve ver CTA de upgrade na seção de temas Pro."""
        client.force_login(user_free)
        response = client.get('/dashboard/page/edit/')
        content = response.content.decode()

        assert 'upgrade' in content.lower() or 'plano Pro' in content

    def test_page_edit_sem_cadeado_para_pro(self, client, user_pro, page_pro):
        """Usuário Pro não deve ver cadeados nos temas."""
        client.force_login(user_pro)
        response = client.get('/dashboard/page/edit/')
        content = response.content.decode()

        assert '🔒' not in content

    def test_page_edit_temas_pro_sem_input_radio_para_free(self, client, user_free, page_free):
        """
        Para usuário Free, os temas Pro não devem ter input radio no HTML —
        impedindo seleção mesmo sem JavaScript.
        """
        client.force_login(user_free)
        response = client.get('/dashboard/page/edit/')
        content = response.content.decode()

        for slug in PRO_THEMES:
            assert f'value="{slug}"' not in content, \
                f'Input radio para tema Pro {slug} encontrado no HTML para usuário Free'

    def test_page_edit_temas_pro_com_input_radio_para_pro(self, client, user_pro, page_pro):
        """Para usuário Pro, todos os temas Pro devem ter input radio no HTML."""
        client.force_login(user_pro)
        response = client.get('/dashboard/page/edit/')
        content = response.content.decode()

        for slug in PRO_THEMES:
            assert f'value="{slug}"' in content, \
                f'Input radio para tema Pro {slug} ausente no HTML para usuário Pro'