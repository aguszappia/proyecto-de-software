"""Handlers para páginas de error en la web."""

from dataclasses import dataclass
from flask import render_template

@dataclass
class HTTPError:
    """Modelo liviano para pasar datos de error al template."""
    code: int
    message: str
    description: str

def not_found(e):
    """Renderizo la vista 404 con un mensaje amigable."""
    error = HTTPError(
        code=404,
        message="Página no encontrada",
        description="La página que buscas no existe."
    )
    return render_template("error.html", error=error), 404

def unauthorized(e):
    """Renderizo la vista 401 cuando falta autenticación."""
    error = HTTPError(
        code=401,
        message="No autorizado",
        description="No tienes permiso para acceder a esta página."
    )
    return render_template("error.html", error=error), 401

def internal_server_error(e):
    """Renderizo la vista 500 con un texto genérico."""
    error = HTTPError(
        code=500,
        message="Error interno del servidor",
        description="Ha ocurrido un error en el servidor. Inténtalo de nuevo más tarde."
    )
    return render_template("error.html", error=error), 500

#error para falta de permisos
def forbidden(e):
    """Renderizo la vista 403 cuando faltan permisos."""
    error = HTTPError(
        code=403,
        message="Error de permisos",
        description="No tenés permisos para acceder a esta sección."
    )
    return render_template("error.html", error=error), 403
