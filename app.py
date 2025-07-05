# app.py
"""
Main application file for the MLB Stats Tracker.
"""
import os
import logging
import threading
from flask import Flask

from config import config_by_name
from extensions import cache
from routes import main_bp
from utils import get_stat_class
from tasks import daily_cache_refresh, warm_cache_on_startup

def create_app(config_name: str = 'development') -> Flask:
    """
    Creates and configures an instance of the Flask application.
    """
    # Point to the root-level static and templates folders
    app = Flask(__name__, static_folder='static', template_folder='templates')
    
    config_object = config_by_name.get(config_name, 'development')
    app.config.from_object(config_object)
    
    # Initialize extensions
    cache.init_app(app)
    
    # Register blueprints
    app.register_blueprint(main_bp)

    # Explicitly register the function as a Jinja2 filter
    app.jinja_env.filters['get_stat_class'] = get_stat_class

    # Configure logging
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    logger = logging.getLogger(__name__)
    logger.info("MLB Stats Tracker application created successfully.")

    return app

config_name = os.getenv('FLASK_CONFIG', 'production')
app = create_app(config_name)

if __name__ == '__main__':
    # The reloader is helpful for local dev, but starts threads twice.
    # For local testing of background tasks, run with: flask run --no-reload
    # Gunicorn on Railway does not use the reloader, so this check is not needed there.
    if not app.debug or os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
        warmup_thread = threading.Thread(target=warm_cache_on_startup, args=(app,), daemon=True)
        refresh_thread = threading.Thread(target=daily_cache_refresh, args=(app,), daemon=True)
        warmup_thread.start()
        refresh_thread.start()

    port = int(os.environ.get('PORT', 5005))
    # The 'debug' flag is now controlled by the Config object.
    # use_reloader=False prevents the duplicate thread issue on Windows.
    app.run(host='0.0.0.0', port=port, use_reloader=False)
