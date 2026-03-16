#!/bin/sh
set -e

echo "==> [Celery] Aguardando banco de dados..."
python << 'EOF'
import os, time, sys
import dj_database_url
import psycopg2
from decouple import config

db_url = config('DATABASE_URL')
params = dj_database_url.parse(db_url)

host     = params.get('HOST', 'db')
port     = params.get('PORT', 5432)
dbname   = params.get('NAME', 'lumebio')
user     = params.get('USER', 'lumebio')
password = params.get('PASSWORD', '')

for i in range(30):
    try:
        psycopg2.connect(
            host=host, port=port,
            dbname=dbname, user=user, password=password,
            connect_timeout=3,
        ).close()
        print("==> [Celery] Banco disponivel!")
        sys.exit(0)
    except Exception as e:
        print(f"   Tentativa {i+1}/30: aguardando db:{port}...")
        time.sleep(2)

print("==> [Celery] ERRO: banco nao respondeu em 60s.")
sys.exit(1)
EOF

echo "==> [Celery] Iniciando: $@"
exec "$@"