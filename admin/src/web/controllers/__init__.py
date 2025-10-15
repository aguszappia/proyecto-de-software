from __future__ import annotations

from flask import Flask

from .sites import sites_admin, sites_public, sites_history

from . import users, tags_admin


def register_controllers(app: Flask) -> None:
    """Adjunto los blueprints principales a la app recibida."""
    app.register_blueprint(users.bp)
    app.register_blueprint(sites_admin.bp)
    app.register_blueprint(sites_public.public_bp)
    app.register_blueprint(sites_history.history_bp)
    app.register_blueprint(tags_admin.bp)


__all__ = ["register_controllers"]
