import os
from threading import Lock

from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()

_client = None
_db = None
_client_signature = None
_client_lock = Lock()


def _build_client(db_uri: str) -> MongoClient:
    # Reuse one MongoClient process-wide to avoid repeated SRV/DNS resolution.
    return MongoClient(
        db_uri,
        serverSelectionTimeoutMS=5000,
        connectTimeoutMS=5000,
        socketTimeoutMS=10000,
        retryWrites=True,
    )


def get_db():
    global _client, _db, _client_signature

    db_uri = os.getenv("DB_URI", "mongodb://localhost:27017")
    db_name = os.getenv("DB_NAME", "airport_ops")
    signature = f"{db_uri}|{db_name}"

    with _client_lock:
        if _db is not None and _client_signature == signature:
            return _db

        _client = _build_client(db_uri)
        _db = _client[db_name]
        _client_signature = signature
        return _db
