from flask import Flask
from flask_cors import CORS
from flask_mysqldb import MySQL
from .config import DevelopmentConfig

# Initialize Flask app
app = Flask(__name__)
app.config.from_object(DevelopmentConfig)

# Setup MySQL
mysql = MySQL(app)

# enable CORS
CORS(app)

# Import routes after app initialization to avoid circular imports
from .routes import films
from .routes import customers
from .routes import actors
