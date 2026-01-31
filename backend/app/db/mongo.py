from flask import current_app
from pymongo import MongoClient
import os

def get_db():
    db_uri = os.getenv("DB_URI")
    db_name = os.getenv("DB_NAME", "airport")  # default to 'airport' if not set
    client = MongoClient(db_uri)
    return client[db_name]
