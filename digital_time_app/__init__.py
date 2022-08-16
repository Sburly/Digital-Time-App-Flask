import os
from flask import Flask
from dotenv import load_dotenv
from pymongo import MongoClient

from digital_time_app.routes import pages

load_dotenv()


def create_app():
    app = Flask(__name__)
    # Define the secret key to have access to cookies
    app.secret_key = ["SECRET_KEY"]
    # Connect to the Mongo Database
    client = MongoClient(os.environ.get("MONGODB_URI"))
    app.db = client.digital_time_app
    # Delete blank lines in the inspector caused by Jinja2
    app.jinja_env.lstrip_blocks = True
    app.jinja_env.trim_blocks = True
    # Register blueprint (routes.py)
    app.register_blueprint(pages)
    return app
