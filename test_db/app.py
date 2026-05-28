from dotenv import load_dotenv
import os
from flask_sqlalchemy import SQLAlchemy
from flask import Flask

app = Flask(__name__)
load_dotenv()
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")
db = SQLAlchemy(app)

with app.app_context():
    db.create_all()
    print("Connected successfully!")