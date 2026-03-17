"""
Testes unitários — analytics/utils e accounts/validators
"""
import pytest, re
from django.core.exceptions import ValidationError

from apps.analytics.utils import anonymize_ip, extract_domain, parse_device
from apps.accounts.validators import (
    RESERVED_SLUGS,
    generate_unique_slug,
    validate_slug_not_reserved,
)


# ─── anonymize_ip ─────────────────────────────────────────────────────────────

class TestAnonymizeIp:

    def test_ipv4_zera_ultimo_octeto(self):
        assert anonymize_ip('192.168.1.42') == '192.168.1.0'

    def test_ipv4_ja_zerado_permanece(self):
        assert anonymize_ip('10.0.0.0') == '10.0.0.0'

    def test_ipv4_preserva_tres_primeiros_octetos(self):
        result = anonymize_ip('203.45.67.89')
        assert result.startswith('203.45.67.')
        assert result.endswith('.0')

    def test_ipv6_mantem_prefixo_48(self):
        result = anonymize_ip('2001:db8:85a3::8a2e:370:7334')
        # /48 preserva os primeiros 3 grupos
        assert result.startswith('2001:db8:85a3')

    def test_ipv6_zera_bits_apos_48(self):
        result = anonymize_ip('2001:db8:85a3:dead:beef:1:2:3')
        assert '::' in result or result.endswith(':0')

    def test_string_vazia_retorna_vazia(self):
        assert anonymize_ip('') == ''

    def test_ip_invalido_retorna_vazia(self):
        assert anonymize_ip('not_an_ip') == ''
        assert anonymize_ip('999.999.999.999') == ''

    def test_none_nao_quebra(self):
        # Chamadas com None não devem lançar exceção — retorna ''
        assert anonymize_ip(None) == ''


# ─── parse_device ─────────────────────────────────────────────────────────────

class TestParseDevice:

    def test_iphone_retorna_mobile(self):
        assert parse_device('Mozilla/5.0 (iPhone; CPU iPhone OS 17)') == 'mobile'

    def test_android_retorna_mobile(self):
        assert parse_device('Mozilla/5.0 (Linux; Android 13; Pixel 7)') == 'mobile'

    def test_windows_phone_retorna_mobile(self):
        assert parse_device('Mozilla/5.0 (compatible; MSIE 10.0; Windows Phone 8.0)') == 'mobile'

    def test_blackberry_retorna_mobile(self):
        assert parse_device('BlackBerry9700/5.0.0.743') == 'mobile'

    def test_ipad_retorna_tablet(self):
        assert parse_device('Mozilla/5.0 (iPad; CPU OS 16_0)') == 'tablet'

    def test_android_tablet_retorna_tablet(self):
        assert parse_device('Mozilla/5.0 (tablet; rv:68.0) Gecko/68.0') == 'tablet'
        
    def test_desktop_windows_retorna_desktop(self):
        assert parse_device('Mozilla/5.0 (Windows NT 10.0; Win64; x64)') == 'desktop'

    def test_desktop_mac_retorna_desktop(self):
        assert parse_device('Mozilla/5.0 (Macintosh; Intel Mac OS X 13_0)') == 'desktop'

    def test_string_vazia_retorna_desktop(self):
        assert parse_device('') == 'desktop'

    def test_case_insensitive(self):
        assert parse_device('MOZILLA/5.0 (IPHONE; CPU)') == 'mobile'


# ─── extract_domain ───────────────────────────────────────────────────────────

class TestExtractDomain:

    def test_extrai_dominio_simples(self):
        assert extract_domain('https://instagram.com/p/abc123') == 'instagram.com'

    def test_remove_www(self):
        assert extract_domain('https://www.google.com/search?q=test') == 'google.com'

    def test_preserva_subdominio_nao_www(self):
        assert extract_domain('https://blog.example.com/post') == 'blog.example.com'

    def test_string_vazia_retorna_vazia(self):
        assert extract_domain('') == ''

    def test_none_retorna_vazia(self):
        assert extract_domain(None) == ''

    def test_url_sem_path(self):
        assert extract_domain('https://twitter.com') == 'twitter.com'

    def test_url_com_porta(self):
        assert extract_domain('http://localhost:8000/path') == 'localhost:8000'


# ─── validate_slug_not_reserved ──────────────────────────────────────────────

class TestValidateSlugNotReserved:

    def test_slug_reservado_levanta_validation_error(self):
        for slug in ['admin', 'dashboard', 'billing', 'api']:
            with pytest.raises(ValidationError):
                validate_slug_not_reserved(slug)

    def test_slug_reservado_case_insensitive(self):
        with pytest.raises(ValidationError):
            validate_slug_not_reserved('ADMIN')
        with pytest.raises(ValidationError):
            validate_slug_not_reserved('Dashboard')

    def test_slug_valido_nao_levanta_erro(self):
        # Não deve lançar exceção
        validate_slug_not_reserved('joaosilva')
        validate_slug_not_reserved('meu-perfil')
        validate_slug_not_reserved('dev2bueno')

    def test_todos_slugs_reservados_bloqueados(self):
        for slug in RESERVED_SLUGS:
            with pytest.raises(ValidationError):
                validate_slug_not_reserved(slug)


# ─── generate_unique_slug ────────────────────────────────────────────────────

class TestGenerateUniqueSlug:

    def test_slug_simples_sem_conflito(self, db):
        assert generate_unique_slug('joaosilva') == 'joaosilva'

    def test_remove_caracteres_invalidos(self, db):
        result = generate_unique_slug('João Silva!')
        assert re.match(r'^[a-z0-9_-]+$', result)
        assert 'silva' in result

    def test_limita_a_50_caracteres(self, db):
        long_slug = 'a' * 100
        assert len(generate_unique_slug(long_slug)) <= 50

    def test_slug_vazio_retorna_user(self, db):
        assert generate_unique_slug('!!!') == 'user'

    def test_slug_reservado_recebe_prefixo(self, db):
        result = generate_unique_slug('admin')
        assert result == 'user-admin'

    def test_conflito_adiciona_sufixo_numerico(self, db, user):
        # 'user@test.com' → slug 'user' já existe via conftest
        # Testa que um segundo slug igual recebe sufixo
        from apps.accounts.models import Profile
        slug_existente = user.profile.slug
        result = generate_unique_slug(slug_existente)
        assert result == f'{slug_existente}1'

    def test_multiplos_conflitos_incrementa(self, db, user_free, user_pro):
        # Cria conflito com o slug do user_free e verifica incremento
        slug_base = user_free.profile.slug
        result = generate_unique_slug(slug_base)
        assert result.startswith(slug_base)
        assert result != slug_base