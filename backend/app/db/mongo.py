from flask import current_app
from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()

def get_db():
    db_uri = os.getenv("DB_URI", "mongodb://localhost:27017")
    db_name = os.getenv("DB_NAME", "airport_ops")  
    # Keep timeouts short so background loops don't stall if DB is unreachable.
    client = MongoClient(db_uri, serverSelectionTimeoutMS=2000, connectTimeoutMS=2000)
    return client[db_name]

