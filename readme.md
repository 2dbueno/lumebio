# 🔗 LumeBio

Plataforma SaaS de **link in bio** brasileira — alternativa ao Linktree com billing nativo via **AbacatePay (Pix)** e analytics integrado.

---

# ✨ Features

• Página pública de links com slug personalizado e domínio customizado  
• Planos **Free** e **Pro** com controle de limites por plano  
• Billing via **AbacatePay (Pix)** utilizando fluxo **Plan → Subscription → Invoice**  
• Analytics de cliques e visualizações com agregação diária via **Celery Beat**  
• Geolocalização aproximada utilizando **GeoIP2** (país e cidade sem coleta de dados pessoais)  
• Exportação e exclusão de dados conforme **LGPD** (Art. 7º I e IX)  
• Temas customizáveis por página  
• Sistema de notificações internas  
• Monitoramento de erros com **Sentry**

---

# 🛠 Stack

| Camada | Tecnologia |
|------|-------------|
| Backend | Django 5.1 + DRF |
| Banco de dados | PostgreSQL 16 |
| Cache / Filas | Redis 7 + Celery |
| Storage | MinIO (local) / S3-compatible |
| Auth | django-allauth |
| Billing | AbacatePay |
| Infra | Docker Compose + Gunicorn |
| Monitoramento | Sentry |

---

# 📁 Estrutura do Projeto

    apps/
    ├── accounts/       # Usuário customizado, perfil, LGPD
    ├── analytics/      # PageViews, LinkClicks, DailyAggregate
    ├── billing/        # Plan, Subscription, Invoice, AbacatePay
    ├── dashboard/      # Painel do usuário autenticado
    ├── notifications/  # Notificações internas
    ├── pages/          # Página pública + blocos de links
    └── themes/         # Temas visuais

    config/             # Settings, URLs, Celery
    core/               # BaseModel, Mixins compartilhados
    docker/             # Dockerfile, Compose, Nginx, scripts

---

# 🚀 Setup Local (Docker)

Pré-requisitos:

• Docker  
• Docker Compose

Passo a passo:

    # 1. Clone o repositório
    git clone https://github.com/2dbueno/lumebio.git
    cd lumebio

    # 2. Configure as variáveis de ambiente
    cp .env.example .env

    # edite o arquivo .env conforme necessário

    # 3. Suba os serviços
    cd docker
    docker compose up --build -d

    # 4. Rode as migrations
    docker exec lumebio_web python manage.py migrate

    # 5. Crie um superusuário
    docker exec -it lumebio_web python manage.py createsuperuser

---

# 🌐 Acessos Locais

    Aplicação:
    http://localhost:8000

    Django Admin:
    http://localhost:8000/admin

    MinIO Console:
    http://localhost:9001

---

# ⚙️ Variáveis de Ambiente

| Variável | Descrição |
|---------|-----------|
| SECRET_KEY | Chave secreta do Django |
| DEBUG | True para desenvolvimento, False para produção |
| DATABASE_URL | URL de conexão PostgreSQL |
| REDIS_URL | URL do Redis |
| SENTRY_DSN | DSN do Sentry (opcional) |
| GEOIP_PATH | Caminho para os arquivos GeoLite2 (.mmdb) |
| EMAIL_HOST | Servidor SMTP |
| EMAIL_HOST_USER | Usuário SMTP |
| EMAIL_HOST_PASSWORD | Senha SMTP |
| MINIO_ENDPOINT | Endpoint do storage |
| MINIO_ACCESS_KEY | Chave de acesso |
| MINIO_SECRET_KEY | Chave secreta |
| MINIO_BUCKET_NAME | Nome do bucket |

Para billing com **AbacatePay**, adicione também:

    ABACATEPAY_API_KEY=
    ABACATEPAY_WEBHOOK_SECRET=

---

# 🧪 Testes

    docker exec lumebio_web pytest

---

# 📄 Licença

Projeto privado — todos os direitos reservados.