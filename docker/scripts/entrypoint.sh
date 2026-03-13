#!/bin/sh
set -e

echo "==> Aguardando banco de dados..."
python << EOF
import os, time, sys
import dj_database_url
import psycopg2
from decouple import config

db_url = config('DATABASE_URL')
params = dj_database_url.parse(db_url)

host = params.get('HOST', 'db')
port = params.get('PORT', 5432)
dbname = params.get('NAME', 'lumebio')
user = params.get('USER', 'lumebio')
password = params.get('PASSWORD', 'lumebio123')

for i in range(30):
    try:
        conn = psycopg2.connect(
            host=host, port=port,
            dbname=dbname, user=user, password=password,
            connect_timeout=3
        )
        conn.close()
        print("==> Banco disponivel!")
        sys.exit(0)
    except Exception as e:
        print(f"   Tentativa {i+1}/30: {e}")
        time.sleep(2)

print("==> ERRO: Banco nao respondeu em 60s.")
sys.exit(1)
EOF

echo "==> Rodando migrations..."
python manage.py migrate --noinput

echo "==> Coletando estaticos..."
python manage.py collectstatic --noinput

echo "==> Iniciando Gunicorn..."
exec gunicorn config.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers 2 \
    --timeout 120 \
    --log-level info \
    --access-logfile - \
    --error-logfile -
