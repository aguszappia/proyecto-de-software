"""Utilidades simples para emitir y validar tokens JWT con HS256."""

from __future__ import annotations

import base64
import json
import hmac
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Tuple

from flask import current_app


class JWTError(RuntimeError):
    """Error base para problemas con JWT."""


class JWTDecodeError(JWTError):
    """Token mal formado o con claims inválidos."""


class JWTSignatureError(JWTError):
    """La firma no coincide con el contenido."""


class JWTExpiredError(JWTError):
    """El token está expirado."""


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(segment: str) -> bytes:
    padding = "=" * (-len(segment) % 4)
    return base64.urlsafe_b64decode(segment + padding)


def _json_dumps(data: Dict[str, Any]) -> bytes:
    return json.dumps(data, separators=(",", ":"), sort_keys=True).encode("utf-8")


def _json_loads(data: bytes) -> Dict[str, Any]:
    return json.loads(data.decode("utf-8"))


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _timestamp(dt: datetime) -> int:
    return int(dt.timestamp())


def _config_secret() -> bytes:
    secret = current_app.config.get("JWT_SECRET_KEY") or current_app.config.get("SECRET_KEY")
    if not secret:
        raise RuntimeError("Configura JWT_SECRET_KEY o SECRET_KEY para emitir JWT.")
    return secret.encode("utf-8")


def _config_algorithm() -> str:
    algorithm = (current_app.config.get("JWT_ALGORITHM") or "HS256").upper()
    if algorithm != "HS256":
        raise RuntimeError(f"Solo se soporta HS256 como algoritmo JWT (recibido: {algorithm}).")
    return algorithm


def _sign(message: str) -> bytes:
    return hmac.new(_config_secret(), message.encode("ascii"), hashlib.sha256).digest()


def _split_token(token: str) -> Tuple[str, str, str]:
    parts = token.split(".")
    if len(parts) != 3:
        raise JWTDecodeError("El token JWT debe tener header.payload.signature.")
    return parts[0], parts[1], parts[2]


def encode_token(payload: Dict[str, Any], *, expires_in: int | None = None, subject: str | None = None) -> str:
    """Emite un JWT con HS256."""
    algorithm = _config_algorithm()
    now = _now()
    claims = dict(payload or {})
    claims.setdefault("iat", _timestamp(now))
    if expires_in is not None:
        claims["exp"] = _timestamp(now + timedelta(seconds=int(expires_in)))
    if subject is not None:
        claims["sub"] = str(subject)
    header = {"alg": algorithm, "typ": "JWT"}
    header_encoded = _b64url_encode(_json_dumps(header))
    payload_encoded = _b64url_encode(_json_dumps(claims))
    signing_input = f"{header_encoded}.{payload_encoded}"
    signature = _b64url_encode(_sign(signing_input))
    return f"{signing_input}.{signature}"


def decode_token(token: str, *, verify_exp: bool = True) -> Dict[str, Any]:
    """Decodifica y valida la firma del JWT y devuelve sus claims."""
    header_segment, payload_segment, signature_segment = _split_token(token)
    signing_input = f"{header_segment}.{payload_segment}"
    expected_signature = _sign(signing_input)
    provided_signature = _b64url_decode(signature_segment)
    if not hmac.compare_digest(expected_signature, provided_signature):
        raise JWTSignatureError("La firma del token es inválida.")

    header = _json_loads(_b64url_decode(header_segment))
    algorithm = header.get("alg")
    if algorithm != _config_algorithm():
        raise JWTDecodeError(f"Algoritmo JWT inesperado: {algorithm}.")

    payload = _json_loads(_b64url_decode(payload_segment))

    if verify_exp:
        expiration = payload.get("exp")
        if expiration is not None:
            if int(expiration) < _timestamp(_now()):
                raise JWTExpiredError("El token expiró.")
    return payload


def get_access_token_ttl() -> int:
    return int(current_app.config.get("JWT_ACCESS_TTL_SECONDS") or 60 * 60)


def get_refresh_token_ttl() -> int:
    return int(current_app.config.get("JWT_REFRESH_TTL_SECONDS") or 60 * 60 * 24 * 30)


def issue_access_token(user_id: int, extra_claims: Dict[str, Any] | None = None) -> str:
    """Emite un access token corto."""
    claims = {"type": "access"}
    if extra_claims:
        claims.update(extra_claims)
    return encode_token(claims, subject=str(user_id), expires_in=get_access_token_ttl())


def issue_refresh_token(user_id: int, extra_claims: Dict[str, Any] | None = None) -> str:
    """Emite un refresh token de larga duración."""
    claims = {
        "type": "refresh",
        "jti": secrets.token_urlsafe(8),
    }
    if extra_claims:
        claims.update(extra_claims)
    return encode_token(claims, subject=str(user_id), expires_in=get_refresh_token_ttl())


def validate_token(token: str, *, expected_type: str | None = None) -> Dict[str, Any]:
    """Decodifica y asegura que el claim type coincida si se indica."""
    payload = decode_token(token)
    if expected_type and payload.get("type") != expected_type:
        raise JWTDecodeError("El tipo de token no coincide con lo esperado.")
    return payload
