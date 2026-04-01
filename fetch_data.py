# fetch_data.py

import logging
from app import create_app
from tasks import warm_cache_on_startup

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if __name__ == '__main__':
    logger.info("🚀 Starting standalone daily data fetch...")
    
    # Create an app context so the cache connects to Redis
    app = create_app()
    
    # Run your existing warm-up logic
    warm_cache_on_startup(app)
    
    logger.info("🏁 Data fetch complete. Shutting down worker.")