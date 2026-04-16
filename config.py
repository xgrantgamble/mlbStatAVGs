# config.py
import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'a-super-secret-key')
    SEND_FILE_MAX_AGE_DEFAULT = 0
    TEMPLATES_AUTO_RELOAD = True
    
    # NEW: Redis Cache settings
    CACHE_TYPE = 'RedisCache'
    CACHE_REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
    CACHE_DEFAULT_TIMEOUT = 172800  

    # Force both apps to use the exact same locker name
    CACHE_KEY_PREFIX = 'mlb_prod'

class DevelopmentConfig(Config):
    DEBUG = True

class ProductionConfig(Config):
    DEBUG = False

config_by_name = {
    'development': DevelopmentConfig,
    'production': ProductionConfig
}