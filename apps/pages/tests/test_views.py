import pytest
from django.urls import reverse
from django.contrib.auth import get_user_model
from apps.pages.models import Page, Block
from apps.accounts.models import Profile

User = get_user_model()


@pytest.fixture
def user(db):
    return User.objects.create_user(email='joao@test.com', password='pass123')


@pytest.fixture
def profile(user):
    return Profile.objects.get(user=user)


@pytest.fixture
def page(user):
    return Page.objects.get(user=user)


def test_pagina_publica_retorna_200(client, profile, page):
    page.is_published = True
    page.save()
    response = client.get(f'/{profile.slug}/')
    assert response.status_code == 200


def test_pagina_nao_publicada_retorna_404(client, profile, page):
    page.is_published = False
    page.save()
    response = client.get(f'/{profile.slug}/')
    assert response.status_code == 404


@pytest.mark.django_db
def test_slug_inexistente_retorna_404(client):
    response = client.get('/usuario-que-nao-existe/')
    assert response.status_code == 404


def test_meta_og_presentes(client, profile, page):
    page.title = 'Minha Página'
    page.is_published = True
    page.save()
    response = client.get(f'/{profile.slug}/')
    assert b'og:title' in response.content
    assert b'og:description' in response.content
    assert b'twitter:card' in response.content


def test_blocos_inativos_nao_aparecem(client, profile, page):
    Block.objects.create(page=page, title='Visível', is_active=True, order=1)
    Block.objects.create(page=page, title='Oculto', is_active=False, order=2)
    page.is_published = True
    page.save()
    response = client.get(f'/{profile.slug}/')
    assert b'Vis\xc3\xadvel' in response.content
    assert b'Oculto' not in response.content


def test_block_redirect(client, page):
    block = Block.objects.create(
        page=page, title='Google', url='https://google.com',
        block_type='link', is_active=True
    )
    response = client.get(f'/r/{block.id}/')
    assert response.status_code == 302
    assert response['Location'] == 'https://google.com'


def test_block_redirect_registra_click(client, page):
    from apps.pages.models import LinkClick
    block = Block.objects.create(
        page=page, title='Google', url='https://google.com',
        block_type='link', is_active=True
    )
    client.get(f'/r/{block.id}/')
    assert LinkClick.objects.filter(block=block).count() == 1
