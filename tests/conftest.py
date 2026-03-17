"""
Fixtures globais compartilhadas entre todos os arquivos de teste.
"""
import pytest
from django.contrib.auth import get_user_model

from apps.accounts.models import Profile
from apps.billing.models import Plan
from apps.pages.models import Block, Page

User = get_user_model()


# ─── Planos ───────────────────────────────────────────────────────────────────

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


# ─── Usuários ─────────────────────────────────────────────────────────────────

@pytest.fixture
def user(db):
    return User.objects.create_user(email='user@test.com', password='pass123')


@pytest.fixture
def user_free(db, plan_free):
    u = User.objects.create_user(email='free@test.com', password='pass123')
    u.profile.plan = 'free'
    u.profile.save(update_fields=['plan'])
    return u


@pytest.fixture
def user_pro(db, plan_pro):
    u = User.objects.create_user(email='pro@test.com', password='pass123')
    u.profile.plan = 'pro'
    u.profile.save(update_fields=['plan'])
    return u


# ─── Profiles ────────────────────────────────────────────────────────────────

@pytest.fixture
def profile(user):
    return Profile.objects.get(user=user)


# ─── Pages ───────────────────────────────────────────────────────────────────

@pytest.fixture
def page(user):
    return Page.objects.get(user=user)


@pytest.fixture
def page_free(user_free):
    return Page.objects.get(user=user_free)


@pytest.fixture
def page_pro(user_pro):
    return Page.objects.get(user=user_pro)


# ─── Blocks ──────────────────────────────────────────────────────────────────

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


# ─── Clients autenticados ────────────────────────────────────────────────────

@pytest.fixture
def logged_client(client, user):
    client.force_login(user)
    return client


@pytest.fixture
def logged_client_free(client, user_free):
    client.force_login(user_free)
    return client


@pytest.fixture
def logged_client_pro(client, user_pro):
    client.force_login(user_pro)
    return client