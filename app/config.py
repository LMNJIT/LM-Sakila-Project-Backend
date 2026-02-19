import os
from dotenv import load_dotenv

load_dotenv()

# Database configuration
class DevelopmentConfig:
    # MySQL settings - loaded from .env file
    MYSQL_HOST = os.getenv('MYSQL_HOST', 'localhost')
    MYSQL_USER = os.getenv('MYSQL_USER', 'root')
    MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD', '')
    MYSQL_DB = os.getenv('MYSQL_DB', 'movie_rental')
    MYSQL_CURSORCLASS = 'DictCursor'  # Returns results as dictionaries
    
    # App settings
    DEBUG = True
    TESTING = False

# Not using these yet but keeping for later
# class ProductionConfig:
#     MYSQL_HOST = os.getenv('MYSQL_HOST', 'localhost')
#     MYSQL_USER = os.getenv('MYSQL_USER', 'root')
#     MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD', '')
#     MYSQL_DB = os.getenv('MYSQL_DB', 'movie_rental')
#     MYSQL_CURSORCLASS = 'DictCursor'
#     DEBUG = False
#     TESTING = False
