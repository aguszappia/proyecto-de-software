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

    API_TOKEN_TTL_SECONDS = int(environ.get("API_TOKEN_TTL_SECONDS", 60 * 60 * 24))
    API_TOKEN_SALT = environ.get("API_TOKEN_SALT", "public-api-token")

    CORS_RESOURCES = [
        r"/api/*"
    ]

    # SQLAlchemy (Base de datos)
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_size": 10,        # tamaño máximo del pool
        "pool_recycle": 60,     # tiempo para reciclar conexiones (segundos)
        "pool_pre_ping": True,  # verifica que la conexión siga activa
    } 
    
    
    # OAuth Google
    AUTHLIB_INSECURE_TRANSPORT = environ.get("AUTHLIB_INSECURE_TRANSPORT", "0")
    GOOGLE_CLIENT_ID = environ.get("GOOGLE_CLIENT_ID", "")
    GOOGLE_CLIENT_SECRET = environ.get("GOOGLE_CLIENT_SECRET", "")
    GOOGLE_REDIRECT_URI = environ.get("GOOGLE_REDIRECT_URI", "http://localhost:5050/api/auth/google/callback")
    GOOGLE_AUTH_SCOPE = ["openid", "email", "profile"]


class ProductionConfig(Config):
    """Apunto a la base productiva usando variables de entorno."""
    SQLALCHEMY_ENGINES = {"default": environ.get("DATABASE_URL") or environ.get("URL")}
    
    MINIO_SERVER = "minio.proyecto2025.linti.unlp.edu.ar"
    MINIO_ACCESS_KEY = environ.get('MINIO_ACCESS_KEY')
    MINIO_SECRET_KEY = environ.get('MINIO_SECRET_KEY')
    MINIO_SECURE = True
    MINIO_BUCKET = "grupo28"
    CORS_ORIGINS = [
        "https://grupo28.proyecto2025.linti.unlp.edu.ar"
    ]
class DevelopmentConfig(Config):
    """Configuro la base local y claves de desarrollo."""
    SECRET_KEY = "your_development_secret_key"

    MINIO_SERVER = "minio.localhost:9000"
    MINIO_ACCESS_KEY = "AsOGiJwynq9UDIrN7tf5"
    MINIO_SECRET_KEY = "Fy2p6U0THpWi27s9fy6ypH7RP1jSWRd4hFaarmPt"
    MINIO_SECURE = False
    MINIO_BUCKET = "grupo28"

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
