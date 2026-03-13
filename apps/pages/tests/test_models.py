import pytest
from django.contrib.auth import get_user_model
from apps.pages.models import Page, Block

User = get_user_model()


@pytest.fixture
def user(db):
    return User.objects.create_user(email='test@test.com', password='pass123')


@pytest.fixture
def page(user):
    return Page.objects.get(user=user)  # criado pelo signal


def test_page_criado_automaticamente(user):
    assert Page.objects.filter(user=user).exists()


def test_theme_vars_neon_dark(page):
    page.theme = 'neon-dark'
    vars = page.get_theme_vars()
    assert vars['bg'] == '#0F0F1A'
    assert vars['primary'] == '#7C3AED'


def test_theme_vars_cyber_blue(page):
    page.theme = 'cyber-blue'
    vars = page.get_theme_vars()
    assert vars['bg'] == '#020B18'


def test_theme_vars_aurora(page):
    page.theme = 'aurora'
    vars = page.get_theme_vars()
    assert vars['accent'] == '#DB2777'


def test_theme_vars_fallback(page):
    page.theme = 'inexistente'
    vars = page.get_theme_vars()
    assert vars['bg'] == '#0F0F1A'  # fallback para neon-dark


def test_block_ordering(page):
    Block.objects.create(page=page, title='B', order=2)
    Block.objects.create(page=page, title='A', order=1)
    blocks = list(page.blocks.values_list('title', flat=True))
    assert blocks[0] == 'A'
    assert blocks[1] == 'B'
