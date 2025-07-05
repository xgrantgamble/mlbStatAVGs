"""
Configuration settings for the MLB Stats Tracker application.
"""
import os

class Config:
    """Base configuration class."""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'a-super-secret-key-that-you-should-change')
    SEND_FILE_MAX_AGE_DEFAULT = 0
    TEMPLATES_AUTO_RELOAD = True
    
    # Flask-Caching settings
    CACHE_TYPE = 'FileSystemCache'
    CACHE_DIR = '/tmp/mlb-cache'
    CACHE_DEFAULT_TIMEOUT = 86400  # 24 hours in seconds

class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True

class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False

# Dictionary to access config classes by name
config_by_name = {
    'development': DevelopmentConfig,
    'production': ProductionConfig
}