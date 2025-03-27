from flask import Blueprint, jsonify, request
from ..app.models import db, Image, Tag, ImageTag
from sqlalchemy import func


bp = Blueprint('api', __name__, url_prefix='/api')


@bp.route('/images/<int:image_id>/tags', methods=['POST'])
def add_tag(image_id):
    """Add tag to image (creates if new)"""
    data = request.get_json()
    if not data or not data.get('name'):
        return jsonify(error="Tag name required"), 400

    image = Image.query.get_or_404(image_id)
    tag_name = data['name'].strip().lower()

    # Validation checks
    if len(image.tags) >= 8:
        return jsonify(error="Max 8 tags per image"), 400
    if any(t.name.lower() == tag_name for t in image.tags):
        return jsonify(error="Tag already exists"), 400

    # Find or create tag
    tag = Tag.query.filter(func.lower(Tag.name) == tag_name).first()
    if not tag:
        tag = Tag(name=tag_name.capitalize())
        db.session.add(tag)

    image.tags.append(tag)
    db.session.commit()
    return jsonify(tag=tag.name, tag_id=tag.id), 201


@bp.route('/images/<int:image_id>/tags/<int:tag_id>', methods=['DELETE'])
def remove_tag(image_id, tag_id):
    """Remove tag association from image"""
    association = ImageTag.query.filter_by(iid=image_id, tid=tag_id).first_or_404()
    db.session.delete(association)
    db.session.commit()
    return jsonify(message="Tag removed"), 200
