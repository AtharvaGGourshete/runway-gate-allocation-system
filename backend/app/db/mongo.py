from flask import current_app
from pymongo import MongoClient

def get_db():
    client = MongoClient(current_app.config["DB_URI"])
    return client.get_default_database()
