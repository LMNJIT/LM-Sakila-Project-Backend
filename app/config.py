import os
from dotenv import load_dotenv

load_dotenv()

# database configuration
class DevelopmentConfig:
    MYSQL_HOST = os.getenv('MYSQL_HOST', 'localhost')
    MYSQL_USER = os.getenv('MYSQL_USER', 'root')
    MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD', '')
    MYSQL_DB = os.getenv('MYSQL_DB', 'movie_rental')
    MYSQL_CURSORCLASS = 'DictCursor'  
    
    DEBUG = True
    TESTING = False

# not using these yet but keeping for later
# class ProductionConfig:
#     MYSQL_HOST = os.getenv('MYSQL_HOST', 'localhost')
#     MYSQL_USER = os.getenv('MYSQL_USER', 'root')
#     MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD', '')
#     MYSQL_DB = os.getenv('MYSQL_DB', 'movie_rental')
#     MYSQL_CURSORCLASS = 'DictCursor'
#     DEBUG = False
#     TESTING = False
