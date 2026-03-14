import ipaddress
from urllib.parse import urlparse


def anonymize_ip(ip: str) -> str:
    """
    Anonimiza IP para conformidade LGPD.
    IPv4: zera o último octeto   → 192.168.1.42  → 192.168.1.0
    IPv6: zera os últimos 80 bits → mantém /48
    """
    if not ip:
        return ''
    try:
        addr = ipaddress.ip_address(ip)
        if addr.version == 4:
            parts = ip.split('.')
            parts[-1] = '0'
            return '.'.join(parts)
        else:
            network = ipaddress.ip_network(f'{ip}/48', strict=False)
            return str(network.network_address)
    except ValueError:
        return ''


def parse_device(user_agent: str) -> str:
    """
    Detecta tipo de dispositivo sem armazenar o user agent bruto.
    Retorna: 'mobile' | 'tablet' | 'desktop'
    """
    ua = user_agent.lower()
    if any(k in ua for k in ['iphone', 'android', 'mobile', 'blackberry', 'windows phone']):
        return 'mobile'
    if any(k in ua for k in ['ipad', 'tablet']):
        return 'tablet'
    return 'desktop'


def extract_domain(referer: str) -> str:
    """
    Extrai só o domínio do referer — não armazena o caminho completo.
    Ex: 'https://instagram.com/p/abc123' → 'instagram.com'
    """
    if not referer:
        return ''
    try:
        parsed = urlparse(referer)
        # Remove www. para agrupar melhor
        return parsed.netloc.replace('www.', '') or ''
    except Exception:
        return ''