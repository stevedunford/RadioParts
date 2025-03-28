from flask import Blueprint, jsonify, request
from ..models import db, Tag

bp = Blueprint('tags', __name__, url_prefix='/tags')


@bp.route('/create', methods=['POST'])
def create_tag():
    data = request.get_json()
    tag = Tag.query.filter_by(name=data['name']).first()

    if not tag:
        tag = Tag(name=data['name'])
        db.session.add(tag)
        db.session.commit()

    # Associate with image if not already
    association = ImageTag.query.filter_by(
        iid=data['image_id'],
        tid=tag.id
    ).first()

    if not association:
        association = ImageTag(iid=data['image_id'], tid=tag.id)
        db.session.add(association)
        db.session.commit()

    return jsonify({'status': 'success', 'tag_id': tag.id})


@bp.route('/', methods=['GET'])
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