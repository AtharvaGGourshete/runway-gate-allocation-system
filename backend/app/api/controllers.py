from flask import Blueprint, jsonify
from app.db.mongo import get_db
from app.db.queries import get_all_flights, get_active_flights

dash = Blueprint("health_api", __name__)

@dash.route("/health", methods=["GET"])
def health_check():
    return jsonify({
        "status": "ok",
        "message": "Backend is running"
    })


@dash.route("/db-check", methods=["GET"])
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

@dash.route("/dashboard")
def all_flights():
    return jsonify(get_all_flights())

def active_flights():
    return jsonify(get_active_flights())