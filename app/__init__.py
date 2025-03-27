from flask import Flask
from .models import db


def create_app():
    app = Flask(__name__, template_folder='templates')

    # Configuration
    app.config.from_mapping(
        SQLALCHEMY_DATABASE_URI='sqlite:///nzvintageradioparts.db',
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SECRET_KEY='750395bab859d353e4a4d0097891ddfb4a15ccff61371b464898947f837dc385'
    )

    # Initialize extensions
    db.init_app(app)

    # Import and register blueprints HERE (after app creation)
    from .routes.images import bp as images_bp
    from .routes.tags import bp as tags_bp

    # Main site routes
    app.register_blueprint(images_bp, url_prefix='/')  # Handles root path

    # API routes
    app.register_blueprint(tags_bp, url_prefix='/api/tags')

    return app
