from flask import Flask, jsonify
from flask_wtf.csrf import CSRFProtect
from .utils import helpers
from .models import db


def create_app():
    app = Flask(__name__, template_folder='templates')

    # Configuration
    app.config.from_mapping(
        SQLALCHEMY_DATABASE_URI='sqlite:///nzvintageradioparts.db',
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SECRET_KEY='9c3ee6247e36a1177178cbe134f31234beefeffe5b8fd8ae4a63cb7cad1cfeba',
        UPLOAD_FOLDER='app/static/images',
        ALLOWED_EXTENSIONS={'gif', 'png', 'jpg', 'jpeg'},
        MAX_CONTENT_LENGTH=16 * 1024 * 1024,  # 16Mb max upload
        WTF_CSRF_TIME_LIMIT=3600,  # 1 hour token expiration
    )

    # Initialize extensions
    csrf = CSRFProtect(app)
    db.init_app(app)

    # Register blueprints
    with app.app_context():
        from .blueprints.parts import bp as parts_bp
        from .blueprints.tags import bp as tags_bp
        from .blueprints.main import bp as main_bp
        from .blueprints.errors import bp as errors_bp

        app.register_blueprint(main_bp)
        app.register_blueprint(parts_bp)
        app.register_blueprint(tags_bp, url_prefix='/tags')
        app.register_blueprint(errors_bp)
        app.helpers = helpers

    # filters for gallery
    @app.template_filter('remove_key')
    def remove_key(d, key):
        d = d.copy()
        d.pop(key, None)
        return d

    return app
