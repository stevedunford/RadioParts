from datetime import timedelta
from flask import Flask, jsonify, session, request
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from .utils import helpers
from .models import db, User
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_talisman import Talisman


def create_app():
    app = Flask(__name__, template_folder='templates')

    Talisman(
        app,
        force_https=False,  # Set to True in production
        strict_transport_security=True,
        session_cookie_secure=True,
        frame_options='SAMEORIGIN',
        content_security_policy={
            'default-src': "'self'",
            'worker-src': [
                "'self'",
                'blob:'  # Required for FilePond's web workers
            ],
            'script-src': [
                "'self'",
                "'unsafe-inline'",  # Required for theme toggle and inline handlers
                'https://cdnjs.cloudflare.com',  # If using external JS libraries
                'https://cdn.jsdelivr.net',  # SortableJS
                'https://unpkg.com'  # FilePond
            ],
            'style-src': [
                "'self'",
                "'unsafe-inline'",  # Required for theme switching
                'https://fonts.googleapis.com',
                'https://cdnjs.cloudflare.com',
                'https://unpkg.com'  # FilePond
            ],
            'font-src': [
                "'self'",
                'https://fonts.gstatic.com',
                'https://cdnjs.cloudflare.com'
            ],
            'img-src': [
                "'self'",
                'data:',  # For inline images/data URIs
                'blob:'  # for FilePond image previews
            ],
            'connect-src': [
                "'self'",  # For AJAX/XHR requests
                'https://unpkg.com'  # If FilePond needs to fetch anything
            ]
        },
    )

    # Rate limiting
    limiter = Limiter(
        app=app,
        key_func=get_remote_address,
        storage_uri="memory://",
        default_limits=["200 per day", "50 per hour"]
    )

    # Configuration
    app.config.from_mapping(
        SQLALCHEMY_DATABASE_URI='sqlite:///nzvintageradioparts.db',
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SECRET_KEY='9c3ee6247e36a1177178cbe134f31234beefeffe5b8fd8ae4a63cb7cad1cfeba',
        UPLOAD_FOLDER='app/static/images',
        ALLOWED_EXTENSIONS={'gif', 'png', 'jpg', 'jpeg'},
        MAX_CONTENT_LENGTH=16 * 1024 * 1024,  # 16Mb max upload
        WTF_CSRF_CHECK_DEFAULT=True,
        WTF_CSRF_TIME_LIMIT=3600,  # 1 hour token expiration
        SESSION_COOKIE_SECURE=True,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE='Lax',
        PERMANENT_SESSION_LIFETIME=timedelta(hours=12)
    )

    # Initialize extensions
    csrf = CSRFProtect(app)
    db.init_app(app)

    # Register blueprints
    with app.app_context():
        from .blueprints.auth import bp as auth_bp
        from .blueprints.parts import bp as parts_bp
        from .blueprints.orders import bp as orders_bp
        from .blueprints.tags import bp as tags_bp
        from .blueprints.main import bp as main_bp
        from .blueprints.errors import bp as errors_bp

        app.register_blueprint(auth_bp, url_prefix='/auth')
        app.register_blueprint(main_bp)
        app.register_blueprint(parts_bp, url_prefix='/parts')
        app.register_blueprint(orders_bp, url_prefix='/orders')
        app.register_blueprint(tags_bp, url_prefix='/tags')
        app.register_blueprint(errors_bp)
        app.helpers = helpers

    # Stricter limits for auth routes
    limiter.limit("10/minute")(app.blueprints['auth'])

    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    @app.before_request
    def enforce_single_session():
        if 'session' in request.cookies and len(request.cookies.getlist('session')) > 1:
            # Clear all session cookies
            session.clear()
            # Force new session
            session['_fresh'] = True

    # filters for gallery
    @app.template_filter('remove_key')
    def remove_key(d, key):
        d = d.copy()
        d.pop(key, None)
        return d

    return app
