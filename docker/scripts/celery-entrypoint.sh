#!/bin/sh
set -e

echo "==> [Celery] Aguardando banco de dados..."
python << 'EOF'
import time, sys
import psycopg2

for i in range(30):
    try:
        psycopg2.connect(
            host="db", port=5432,
            dbname="lumebio", user="lumebio",
            password="lumebio123", connect_timeout=3
        ).close()
        print("==> [Celery] Banco disponivel!")
        sys.exit(0)
    except Exception as e:
        print(f"   Tentativa {i+1}/30: aguardando db:5432...")
        time.sleep(2)

sys.exit(1)
EOF

echo "==> [Celery] Iniciando: $@"
exec "$@"
