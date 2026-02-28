"""Flask application factory."""
from flask import Flask


def create_app(config=None):
    """Create and configure the Flask application."""
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config.from_object("app.config.DefaultConfig")
    if config:
        print(config)
        app.config.update(config)

    from app.routes.pages import pages_bp
    from app.routes.api import api_bp

    app.register_blueprint(pages_bp)
    app.register_blueprint(api_bp, url_prefix="/api")

    return app
