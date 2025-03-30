from flask import Blueprint, jsonify
from flask_wtf.csrf import CSRFError


bp = Blueprint('errors', __name__)


@bp.app_errorhandler(400)
def bad_request(e):
    return jsonify(error=str(e.description) if hasattr(e, 'description') else str(e)), 400


@bp.app_errorhandler(404)
def not_found(e):
    return jsonify(error="Resource not found"), 404


@bp.app_errorhandler(500)
def server_error(e):
    return jsonify(error="Internal server error"), 500


@bp.app_errorhandler(CSRFError)
def handle_csrf_error(e):
    return jsonify({
        'error': 'CSRF token validation failed',
        'message': str(e.description)
    }), 400
