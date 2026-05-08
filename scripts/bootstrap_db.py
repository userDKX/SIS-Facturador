"""Crea la DB local y aplica las migraciones SQL.

Uso:
    python scripts/bootstrap_db.py

Lee DATABASE_URL del .env. Conecta primero a la DB de mantenimiento
(postgres) para crear la DB target si no existe, luego aplica todas las
migraciones de migrations/*.sql en orden alfabetico.
"""

from __future__ import annotations

import sys
from pathlib import Path
from urllib.parse import urlparse

import psycopg
from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(REPO_ROOT / ".env")

import os

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    print("DATABASE_URL no esta en .env", file=sys.stderr)
    sys.exit(1)

parsed = urlparse(DATABASE_URL)
db_name = parsed.path.lstrip("/")
admin_url = DATABASE_URL.replace(f"/{db_name}", "/postgres", 1)


def ensure_database() -> None:
    with psycopg.connect(admin_url, autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (db_name,))
            if cur.fetchone():
                print(f"DB {db_name} ya existe")
                return
            cur.execute(f'CREATE DATABASE "{db_name}"')
            print(f"DB {db_name} creada")


def apply_migrations() -> None:
    migrations_dir = REPO_ROOT / "migrations"
    sql_files = sorted(migrations_dir.glob("*.sql"))
    if not sql_files:
        print("No hay migraciones en migrations/")
        return

    with psycopg.connect(DATABASE_URL) as conn:
        for sql_file in sql_files:
            print(f"Aplicando {sql_file.name}...")
            sql = sql_file.read_text(encoding="utf-8")
            with conn.cursor() as cur:
                cur.execute(sql)
        conn.commit()
    print(f"{len(sql_files)} migracion(es) aplicada(s)")


if __name__ == "__main__":
    ensure_database()
    apply_migrations()
    print("Bootstrap OK")
