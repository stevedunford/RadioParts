from flask import Blueprint, jsonify, request
from ..models import db, Tag

bp = Blueprint('tags', __name__, url_prefix='/api/tags')


@bp.route('', methods=['GET'])
def get_tags():
    """List all tags"""
    tags = Tag.query.all()
    return jsonify([tag.to_dict() for tag in tags])


@bp.route('/<int:tag_id>', methods=['DELETE'])
def delete_tag(tag_id):
    """Delete unused tag"""
    tag = Tag.query.get_or_404(tag_id)
    if tag.images:
        return jsonify(error="Tag is in use"), 400
 
    db.session.delete(tag)
    db.session.commit()
    return jsonify(message="Tag deleted"), 200