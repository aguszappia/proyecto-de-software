from dataclasses import dataclass
from flask import render_template

@dataclass
class HTTPError:
    code: int
    message: str
    description: str

def not_found(e):
    error = HTTPError(
        code=404,
        message="Página no encontrada",
        description="La página que buscas no existe."
    )
    return render_template("error.html", error=error), 404

def unauthorized(e):
    error = HTTPError(
        code=401,
        message="No autorizado",
        description="No tienes permiso para acceder a esta página."
    )
    return render_template("error.html", error=error), 401

def internal_server_error(e):
    error = HTTPError(
        code=500,
        message="Error interno del servidor",
        description="Ha ocurrido un error en el servidor. Inténtalo de nuevo más tarde."
    )
    return render_template("error.html", error=error), 500