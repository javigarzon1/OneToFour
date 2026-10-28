"""Límite de uso: utilidades puras. Los contadores viven en la tabla quiz.limites_uso."""
from __future__ import annotations

import hashlib
import os
from collections.abc import Mapping

# Cabeceras con la IP real del cliente, de más a menos fiable. En Vercel,
# x-vercel-forwarded-for la pone la plataforma y el cliente no puede falsearla.
IP_HEADERS = ("x-vercel-forwarded-for", "x-real-ip", "x-forwarded-for")


def env_int(name: str, default: int, minimum: int = 1) -> int:
    """Lee un entero de una variable de entorno; si no es válido usa ``default``."""
    try:
        value = int(os.getenv(name, "").strip())
    except ValueError:
        return default
    return value if value >= minimum else default


def client_ip(headers: Mapping[str, str], fallback: str | None = None) -> str:
    for name in IP_HEADERS:
        value = headers.get(name)
        if value:
            first = value.split(",")[0].strip()
            if first:
                return first
    return fallback or "desconocida"


def rate_key(ip: str, scope: str, salt: str | None = None) -> str:
    """Clave anónima: no se guarda la IP en claro."""
    salt = salt if salt is not None else os.getenv("RATE_LIMIT_SALT", "onetofour")
    digest = hashlib.sha256(f"{salt}:{ip}".encode("utf-8")).hexdigest()[:24]
    return f"{scope}:{digest}"


def window_start(now: float, window_seconds: int) -> int:
    """Inicio (epoch en segundos) de la ventana fija que contiene ``now``."""
    return int(now // window_seconds * window_seconds)


def retry_after(now: float, window_seconds: int) -> int:
    """Segundos hasta que empiece la siguiente ventana (mínimo 1)."""
    return max(1, window_start(now, window_seconds) + window_seconds - int(now))
