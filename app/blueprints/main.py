from flask import Blueprint, jsonify


bp = Blueprint('main', __name__)


@bp.route('/')
def index():
    return "Welcome to NZ Vintage Radio Parts"


@bp.route('/validate_csrf', methods=['POST'])
def validate_csrf():
    return jsonify({'status': 'valid'}), 200
