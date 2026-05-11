"""
FarmLink Poultry — AI-Enhanced Flock Management and Bird Identification System
Multi-file Flask app (SQLite portable).

Install:
  python -m pip install -r requirements.txt

Run:
  python app.py

Default admin (seeded on first run):
  username=admin
  password=admin123
"""

from __future__ import annotations

import os

from flask import Flask
from flask_login import LoginManager

from config import Config, config_by_name
from models import User, db
from security import bcrypt
from seed import seed_admin_user, seed_sample_data_if_empty

def create_app() -> Flask:
    app = Flask(__name__)
    
    # Load configuration
    config_name = os.environ.get("FLASK_ENV", "development")
    app.config.from_object(config_by_name.get(config_name, config_by_name["default"]))
    
    # Override specific settings if needed
    app.config["SECRET_KEY"] = os.environ.get("FARMLINK_SECRET_KEY", "dev-secret-change-me")
    
    # Database configuration will be handled by Config class
    app.config["SQLALCHEMY_DATABASE_URI"] = Config().SQLALCHEMY_DATABASE_URI
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)
    bcrypt.init_app(app)

    login_manager = LoginManager(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message_category = "warning"

    @login_manager.user_loader
    def load_user(user_id: str):
        try:
            return db.session.get(User, int(user_id))
        except Exception:
            return None

    # Register blueprints
    from routes.auth import bp as auth_bp
    from routes.main import bp as main_bp
    from routes.api import bp as api_bp
    from routes.users import bp as users_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(users_bp)

    # Make config available in templates
    @app.context_processor
    def inject_config():
        return dict(config=Config)

    with app.app_context():
        db.create_all()
        seed_admin_user(bcrypt)
        seed_sample_data_if_empty()

    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)

