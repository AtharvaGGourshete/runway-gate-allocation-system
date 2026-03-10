from app.factory import create_app
import configparser
import os

config = configparser.ConfigParser()
config.read(os.path.abspath(".ini"))

app = create_app()
debug = os.getenv("FLASK_DEBUG", "0") == "1"
app.config["DEBUG"] = debug

# Keep backward-compatibility with existing .ini-based config, but allow env-based
# configuration via app/db/mongo.py.
try:
    app.config["DB_URI"] = config["PROD"]["DB_URI"]
except Exception:
    pass

if __name__ == "__main__":
    # Avoid Flask debug tooling that may rely on shared memory in constrained environments.
    app.run(port=5000, debug=debug, use_reloader=False)
    
