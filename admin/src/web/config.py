class Config:
    TESTING = False
    SECRET_KEY = "your_secret_key"
    SESSION_TYPE = "filesystem"

class ProductionConfig(Config):
    pass

class DevelopmentConfig(Config):
    SECRET_KEY = "your_development_secret_key"

class TestingConfig(Config):
    TESTING = True

config={
    'production': ProductionConfig,
    'development': DevelopmentConfig,
    'testing': TestingConfig
}