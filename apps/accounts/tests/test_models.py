import pytest
from apps.accounts.models import CustomUser, Profile


@pytest.mark.django_db
class TestCustomUser:
    def test_criar_usuario_cria_perfil(self):
        user = CustomUser.objects.create_user(
            email='teste@lumebio.com',
            password='senha123'
        )
        assert Profile.objects.filter(user=user).exists()

    def test_slug_gerado_automaticamente(self):
        user = CustomUser.objects.create_user(
            email='joao@lumebio.com',
            password='senha123'
        )
        assert user.profile.slug == 'joao'

    def test_slug_reservado_gera_prefixo(self):
        user = CustomUser.objects.create_user(
            email='admin@lumebio.com',
            password='senha123'
        )
        assert user.profile.slug != 'admin'

    def test_superuser_criado_corretamente(self):
        user = CustomUser.objects.create_superuser(
            email='super@lumebio.com',
            password='senha123'
        )
        assert user.is_staff is True
        assert user.is_superuser is True
