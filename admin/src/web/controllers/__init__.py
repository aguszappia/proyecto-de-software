"""Application controllers registration."""

from __future__ import annotations

from flask import Flask

from . import users


def register_controllers(app: Flask) -> None:
    """Register application blueprints."""
    app.register_blueprint(users.bp)


__all__ = ["register_controllers"]
