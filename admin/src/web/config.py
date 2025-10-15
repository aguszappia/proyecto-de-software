"""Configuraciones de entorno para la app Flask."""

from os import environ
from datetime import timedelta

class Config:
    """Defino la configuración base compartida por todos los entornos."""
    TESTING = False
    SECRET_KEY = "your_secret_key"
    # Flask-Session: almacena server-side (evitá client-side)
    SESSION_TYPE = "filesystem"
    SESSION_PERMANENT = True
    PERMANENT_SESSION_LIFETIME = timedelta(hours=1)  # duración de la sesión
    SESSION_REFRESH_EACH_REQUEST = True  # extiende expiración con actividad

    # Cookies más seguras
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = environ.get("SESSION_COOKIE_SECURE", "true").strip().lower() == "true"

    # SQLAlchemy (Base de datos)
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_size": 10,        # tamaño máximo del pool
        "pool_recycle": 60,     # tiempo para reciclar conexiones (segundos)
        "pool_pre_ping": True,  # verifica que la conexión siga activa
    } 

class ProductionConfig(Config):
    """Apunto a la base productiva usando variables de entorno."""
    SQLALCHEMY_ENGINES = {"default": environ.get('DATABASE_URL')}

class DevelopmentConfig(Config):
    """Configuro la base local y claves de desarrollo."""
    SECRET_KEY = "your_development_secret_key"

    # variables de entorno para cada miembro
    DB_USER = environ.get('DB_USER', 'postgres')
    DB_PASSWORD = environ.get('DB_PASSWORD', 'admin')
    DB_HOST = environ.get('DB_HOST', 'localhost')
    DB_PORT = environ.get('DB_PORT', '5432')
    DB_NAME = environ.get('DB_NAME', 'grupo28')
    DB_SCHEME = environ.get('DB_SCHEME', 'postgresql+psycopg2')
    
    SQLALCHEMY_ENGINES = {
        "default": f"{DB_SCHEME}://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    }

class TestingConfig(Config):
    """Ajusto la app para correr tests sin efectos secundarios."""
    TESTING = True

config={
    'production': ProductionConfig,
    'development': DevelopmentConfig,
    'testing': TestingConfig
}
