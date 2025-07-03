import os
from dotenv import load_dotenv
from config.database import DatabaseConfig

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    SQLALCHEMY_DATABASE_URI = DatabaseConfig.get_mysql_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
        'connect_args': {
            'connect_timeout': 60,
            'read_timeout': 60,
            'write_timeout': 60
        }
    }
    
    # Payment Processing Config
    MAX_PAYMENT_AMOUNT = float(os.environ.get('MAX_PAYMENT_AMOUNT', 10000.00))
    MIN_PAYMENT_AMOUNT = float(os.environ.get('MIN_PAYMENT_AMOUNT', 0.01))
    SUPPORTED_CURRENCIES = os.environ.get('SUPPORTED_CURRENCIES', 'USD,EUR,GBP,JPY,CAD').split(',')
    
    # API Configuration
    API_HOST = os.environ.get('API_HOST', '0.0.0.0')
    API_PORT = int(os.environ.get('API_PORT', 5000))
    DEBUG = os.environ.get('DEBUG', 'True').lower() == 'true'

class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = DatabaseConfig.get_mysql_uri()

class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = DatabaseConfig.get_test_mysql_uri()
    WTF_CSRF_ENABLED = False

class ProductionConfig(Config):
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = DatabaseConfig.get_mysql_uri()

config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}