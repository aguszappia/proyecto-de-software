from os import environ

class Config:
    TESTING = False
    SECRET_KEY = "your_secret_key"
    SESSION_TYPE = "filesystem"

class ProductionConfig(Config):
    SQLALCHEMY_ENGINES = {"default": environ.get('DATABASE_URL')}

class DevelopmentConfig(Config):
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
    TESTING = True

config={
    'production': ProductionConfig,
    'development': DevelopmentConfig,
    'testing': TestingConfig
}