from flask import Flask
from flask_cors import CORS
import random
import threading
import time
from app.utils.json_encoder import MongoJSONProvider
from app.api.controllers import dash
from app.services.scheduler_service import scheduler_loop

def create_app():
    app = Flask(__name__)
    CORS(app, origins=["http://localhost:3000"])
    app.json = MongoJSONProvider(app)
    app.register_blueprint(dash, url_prefix="/api")
    threading.Thread(target=scheduler_loop, daemon=True).start()
    return app