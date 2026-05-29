from dotenv import load_dotenv
import os
from flask import Flask
from models import db


def create_app(config=None):
    load_dotenv()
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL", "sqlite:///:memory:")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    if config:
        app.config.update(config)

    db.init_app(app)

    from routes import api
    app.register_blueprint(api, url_prefix="/api")

    return app


if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        db.create_all()
        print("Connected successfully!")
    app.run(debug=True)
