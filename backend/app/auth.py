import hashlib
import os
import secrets
import uuid
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

PASSWORD_ITERATIONS = 310_000
JWT_TTL_SECONDS = 7 * 24 * 60 * 60
bearer = HTTPBearer(auto_error=False)

def password_hash(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, PASSWORD_ITERATIONS)
    return "pbkdf2_sha256$" + str(PASSWORD_ITERATIONS) + "$" + salt.hex() + "$" + digest.hex()

def password_verify(password: str, encoded: str) -> bool:
    try:
        algorithm, iterations, salt_hex, digest_hex = encoded.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        actual = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt_hex), int(iterations))
        return secrets.compare_digest(actual.hex(), digest_hex)
    except (ValueError, TypeError):
        return False

def jwt_secret() -> str:
    value = os.getenv("JWT_SECRET", "")
    if len(value) < 32:
        raise RuntimeError("JWT_SECRET debe existir y tener al menos 32 caracteres.")
    return value

def create_access_token(usuario_id: str, usuario: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {"sub": usuario_id, "usuario": usuario, "iat": now, "exp": now + timedelta(seconds=JWT_TTL_SECONDS)}
    return jwt.encode(payload, jwt_secret(), algorithm="HS256")

def current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer)):
    if not credentials:
        raise HTTPException(status_code=401, detail="Debes iniciar sesión.")
    try:
        payload = jwt.decode(credentials.credentials, jwt_secret(), algorithms=["HS256"])
        if not payload.get("sub") or not payload.get("usuario"):
            raise ValueError()
        return payload
    except (jwt.InvalidTokenError, ValueError):
        raise HTTPException(status_code=401, detail="Sesión no válida o expirada.")
