#extensions.py

"""
Initializes Flask extensions to avoid circular imports.
"""
from flask_caching import Cache

cache = Cache()
