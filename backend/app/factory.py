from flask import Flask
from flask_cors import CORS
from app.utils.json_encoder import MongoJSONProvider
from app.api.controllers import dash

def create_app():
    app = Flask(__name__)
    CORS(app, origins=["http://localhost:3000"])
    app.json = MongoJSONProvider(app)
    app.register_blueprint(dash, url_prefix="/api")
    return app