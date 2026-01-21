from app.factory import create_app
import configparser
import os

config = configparser.ConfigParser()
config.read(os.path.abspath(".ini"))

app = create_app()
app.config["DEBUG"] = True
app.config["DB_URI"] = config["PROD"]["DB_URI"]

if __name__ == "__main__":
    app.run(port=5000)
