# app.py
import os
import logging
from flask import Flask

from config import config_by_name
from extensions import cache
from routes import main_bp
from utils import get_stat_class

def create_app(config_name: str = 'development') -> Flask:
    app = Flask(__name__, static_folder='static', template_folder='templates')
    
    config_object = config_by_name.get(config_name, 'development')
    app.config.from_object(config_object)
    
    cache.init_app(app)
    app.register_blueprint(main_bp)
    app.jinja_env.filters['get_stat_class'] = get_stat_class

    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    return app

config_name = os.getenv('FLASK_CONFIG', 'production')
app = create_app(config_name)

# NOTE: Threading code completely removed! 
# The web server now ONLY serves web pages.

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5005))
    app.run(host='0.0.0.0', port=port, use_reloader=False)