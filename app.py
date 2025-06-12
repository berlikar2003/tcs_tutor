import os
import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# SQLAlchemy base setup
class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

# Create Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key-change-in-production")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# ✅ Construct DB path using Flask's instance_path
db_path = os.path.join(app.instance_path, "assessment_system.db")
app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path}"
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Ensure instance folder exists
os.makedirs(app.instance_path, exist_ok=True)

# Initialize DB with app
db.init_app(app)

# Create tables inside app context
with app.app_context():
    import models  # ✅ Import AFTER db.init_app(app)
    db.create_all()
    logging.info("✅ Database tables created")

# Register routes
from routes import bp
app.register_blueprint(bp)
