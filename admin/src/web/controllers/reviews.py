"""Re-export del blueprint de moderación de reseñas.

Se mantiene este módulo para no modificar los imports existentes en la app.
"""

from src.web.controllers.sites.sites_reviews import bp as reviews_bp

__all__ = ["reviews_bp"]
