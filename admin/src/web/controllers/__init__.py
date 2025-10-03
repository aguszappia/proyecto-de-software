"""Application controllers registration."""

from __future__ import annotations

from flask import Flask

from . import users, sites_admin, sites_public


def register_controllers(app: Flask) -> None:
    """Register application blueprints."""
    app.register_blueprint(users.bp)
    app.register_blueprint(sites_admin.bp)
    app.register_blueprint(sites_public.public_bp)
    # app.register_blueprint(tags.bp)


__all__ = ["register_controllers"]
