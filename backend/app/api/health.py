from flask import Blueprint, jsonify
from app.db.mongo import get_db

health_api = Blueprint("health_api", __name__)

@health_api.route("/health", methods=["GET"])
def health_check():
    return jsonify({
        "status": "ok",
        "message": "Backend is running"
    })


@health_api.route("/db-check", methods=["GET"])
def db_check():
    try:
        db = get_db()

        # Ping the database
        db.command("ping")

        # List collections
        collections = db.list_collection_names()

        return jsonify({
            "db_connected": True,
            "database": db.name,
            "collections": collections
        })

    except Exception as e:
        return jsonify({
            "db_connected": False,
            "error": str(e)
        }), 500
