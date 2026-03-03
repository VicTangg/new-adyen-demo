"""Flask application factory."""
from flask import Flask
from werkzeug.middleware.proxy_fix import ProxyFix


def create_app(config=None):
    """Create and configure the Flask application."""
    app = Flask(__name__, template_folder="templates", static_folder="static")
    # Trust X-Forwarded-Proto/Host when behind ngrok or other reverse proxies
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
    app.config.from_object("app.config.DefaultConfig")
    if config:
        print(config)
        app.config.update(config)

    from app.routes.pages import pages_bp
    from app.routes.api import api_bp

    app.register_blueprint(pages_bp)
    app.register_blueprint(api_bp, url_prefix="/api")

    return app
