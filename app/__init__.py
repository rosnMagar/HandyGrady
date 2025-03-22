from flask import Flask
from config import Config
from .extensions import db, login_manager, bcrypt, migrate

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize extensions
    db.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'login'
    login_manager.login_message_category = 'info'
    migrate.init_app(app, db)

    # Import and register routes
    from .routes import init_routes
    init_routes(app)

    return app