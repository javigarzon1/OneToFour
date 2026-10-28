"""Conexión a PostgreSQL (Neon)."""
from __future__ import annotations

import os

import psycopg
from psycopg.rows import dict_row

# Vercel (integración con Neon) define DATABASE_URL y POSTGRES_URL.
URL_VARIABLES = ("DATABASE_URL", "POSTGRES_URL")


def database_url() -> str | None:
    for name in URL_VARIABLES:
        value = os.getenv(name)
        if value and value.strip():
            return value.strip()
    return None


def get_connection():
    """Abre una conexión nueva. Úsala como gestor de contexto.

    ``with get_connection() as connection`` confirma la transacción al salir
    sin errores, la revierte si hay una excepción y cierra la conexión.

    Las filas se devuelven como diccionarios. ``prepare_threshold=None``
    desactiva las sentencias preparadas, necesario con el pooler de Neon
    (PgBouncer en modo transacción).
    """
    url = database_url()
    if not url:
        raise RuntimeError(
            "Falta la variable de entorno DATABASE_URL (cadena de conexión de Neon)."
        )
    return psycopg.connect(
        url,
        row_factory=dict_row,
        connect_timeout=10,
        prepare_threshold=None,
    )
