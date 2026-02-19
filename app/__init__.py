from flask import Flask
from flask_cors import CORS
from flask_mysqldb import MySQL
from .config import DevelopmentConfig

# iitialize Flask app
app = Flask(__name__)
app.config.from_object(DevelopmentConfig)

# setup MySQL
mysql = MySQL(app)

# enable CORS
CORS(app)

from .routes import films
from .routes import customers
from .routes import actors
