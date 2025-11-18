"""Inicializo el cliente OAuth compartido por la aplicación."""

from authlib.integrations.flask_client import OAuth

oauth = OAuth()

__all__ = ["oauth"]
