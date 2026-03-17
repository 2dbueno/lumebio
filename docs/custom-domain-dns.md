# Domínio Customizado — Processo de Apontamento DNS

## Visão geral

Usuários Pro podem apontar qualquer domínio próprio para sua página bio no LumeBio.
O roteamento é feito via `CustomDomainMiddleware` que intercepta o host da requisição
e serve a página do perfil correspondente sem redirecionar o usuário.

## Passo a passo para o usuário

### 1. Configurar no LumeBio

Acesse **Configurações → Domínio Customizado** e informe seu domínio sem `https://`.
Exemplo: `bio.meusite.com.br`

### 2. Adicionar registro CNAME no provedor DNS

| Campo | Valor |
|-------|-------|
| Tipo | `CNAME` |
| Nome/Host | seu subdomínio (ex: `bio`) |
| Valor/Destino | `lumebio.dev` |
| TTL | `3600` (ou automático) |

> Para domínio raiz (ex: `meusite.com` sem subdomínio), use registro `A` apontando
> para o IP do servidor, pois registros CNAME não são permitidos no apex DNS.

### 3. Aguardar propagação

A propagação DNS leva de alguns minutos até 48 horas dependendo do provedor e do TTL anterior.

Verifique com:
```bash
dig CNAME bio.meusite.com.br
# ou
nslookup bio.meusite.com.br
```

### 4. SSL/TLS

Em produção, o Nginx deve estar configurado com certificado wildcard ou usar
Let's Encrypt com validação DNS para cobrir domínios customizados.
Consulte `docs/nginx-ssl.md` quando disponível.

## Implementação técnica

### Middleware (`apps/accounts/middleware.py`)

O `CustomDomainMiddleware` é executado a cada requisição:

1. Extrai o host sem porta (`request.get_host().split(':')[0]`)
2. Ignora hosts da plataforma (`localhost`, `127.0.0.1`, `lumebio.dev`)
3. Ignora paths de sistema (`/admin`, `/static`, `/dashboard`, etc.)
4. Busca `Profile` com `custom_domain == host` **e** `plan == 'pro'`
5. Se encontrado, chama `public_page(request, username=profile.slug)` internamente

### Restrição de plano (BK-40)

A query no middleware filtra `plan=Profile.PLAN_PRO`. Se o usuário fizer downgrade
para Free, o domínio customizado para de funcionar automaticamente — o middleware
simplesmente não encontra o perfil e passa a requisição adiante.

A UI também bloqueia a configuração para usuários Free via `profile.is_pro`.

### Campo no banco

`Profile.custom_domain` — `CharField(max_length=255, blank=True, null=True, unique=True)`

Já existe no model. Nenhuma migration adicional necessária.

## Provedores DNS comuns

| Provedor | Onde configurar |
|----------|----------------|
| Registro.br | painel.registro.br → Zona DNS |
| Cloudflare | Dashboard → DNS → Add record |
| GoDaddy | My Products → DNS |
| HostGator | cPanel → Zone Editor |