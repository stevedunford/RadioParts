from flask import Flask, jsonify
from .models import db


def create_app():
    app = Flask(__name__, template_folder='templates')

    # Configuration
    app.config.from_mapping(
        SQLALCHEMY_DATABASE_URI='sqlite:///nzvintageradioparts.db',
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SECRET_KEY='dc3ee6c47e36f8677178cbe134f32087d3a6effe5b8fd8ae4363cb74cd1cfeba'
    )

    # Initialize extensions
    db.init_app(app)

    # Import and register blueprints HERE (after app creation)
    from .routes.images import bp as images_bp
    from .routes.tags import bp as tags_bp

    # Main site routes
    app.register_blueprint(images_bp)  # Handles root path

    # Tag routes
    app.register_blueprint(tags_bp, url_prefix='/tags')

    # Ensure JSON responses for errors
    @app.errorhandler(404)
    def handle_404(e):
        return jsonify(error=str(e)), 404

    @app.errorhandler(500)
    def handle_500(e):
        return jsonify(error="Internal server error"), 500

    return app
