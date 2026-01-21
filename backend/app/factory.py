from flask import Flask
from flask_cors import CORS
from app.utils.json_encoder import MongoJSONProvider
from app.api.health import health_api

def create_app():
    app = Flask(__name__)

    CORS(app, origins=["http://localhost:3000"])

    # NEW Flask 2.3+ JSON system
    app.json = MongoJSONProvider(app)

    app.register_blueprint(health_api, url_prefix="/api")

    return app
