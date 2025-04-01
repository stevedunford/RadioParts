from flask import Blueprint, request, jsonify
from ..models import db, Tag, Part
from sqlalchemy import func
from datetime import datetime


bp = Blueprint('tags', __name__, url_prefix='/api/tags')


# Get all tags with counts
@bp.route('/', methods=['GET'])
def get_tags():
    try:
        include_unused = request.args.get('include_unused', 'false').lower() == 'true'
        query = db.session.query(
            Tag.id,
            Tag.name,
            Tag.slug,
            func.count(Part.id).label('part_count')
        ).outerjoin(
            Tag.parts
        ).group_by(
            Tag.id
        )

        if not include_unused:
            query = query.having(func.count(Part.id) > 0)

        tags = query.order_by(Tag.name).all()

        return jsonify([{
            'id': tag.id,
            'name': tag.name,
            'slug': tag.slug,
            'part_count': tag.part_count
        } for tag in tags])

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# Create new tag
@bp.route('/', methods=['POST'])
def create_tag():
    try:
        data = request.get_json()
        if not data or 'name' not in data:
            return jsonify({'error': 'Name is required'}), 400

        tag = Tag(name=data['name'], description=data.get('description'))
        db.session.add(tag)
        db.session.commit()

        return jsonify({
            'id': tag.id,
            'name': tag.name,
            'slug': tag.slug
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400


# Get single tag details
@bp.route('/<int:tag_id>', methods=['GET'])
def get_tag(tag_id):
    try:
        tag = Tag.query.get_or_404(tag_id)
        return jsonify({
            'id': tag.id,
            'name': tag.name,
            'slug': tag.slug,
            'description': tag.description,
            'created_at': tag.created_at.isoformat(),
            'part_count': len(tag.parts)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 404


# Update tag
@bp.route('/<int:tag_id>', methods=['PUT'])
def update_tag(tag_id):
    try:
        tag = Tag.query.get_or_404(tag_id)
        data = request.get_json()

        if 'name' in data:
            tag.name = data['name']
            tag.slug = slugify(data['name'])  # Regenerate slug

        if 'description' in data:
            tag.description = data['description']

        db.session.commit()
        return jsonify({
            'id': tag.id,
            'name': tag.name,
            'slug': tag.slug
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400


# Delete tag
@bp.route('/<int:tag_id>', methods=['DELETE'])
def delete_tag(tag_id):
    try:
        tag = Tag.query.get_or_404(tag_id)
        db.session.delete(tag)
        db.session.commit()
        return '', 204
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400


# Add tag to part (existing route - enhanced)
@bp.route('/parts', methods=['POST'])
def add_part_tag():
    try:
        data = request.get_json()
        if not data or 'name' not in data or 'part_id' not in data:
            return jsonify({'error': 'Tag name and part_id required'}), 400

        tag_name = data['name'].strip()
        part_id = data['part_id']

        if not tag_name:
            return jsonify({'error': 'Empty tag name'}), 400

        part = Part.query.get_or_404(part_id)

        # Check if already tagged
        if any(t.name.lower() == tag_name.lower() for t in part.tags):
            return jsonify({'error': 'Part already has this tag'}), 400

        # Find or create tag
        tag = Tag.query.filter(func.lower(Tag.name) == tag_name.lower()).first()
        is_new = False

        if not tag:
            tag = Tag(name=tag_name)
            db.session.add(tag)
            is_new = True

        part.tags.append(tag)
        db.session.commit()

        return jsonify({
            'id': tag.id,
            'name': tag.name,
            'slug': tag.slug,
            'is_new': is_new,
            'part_id': part.id
        }), 201 if is_new else 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400


# Remove tag from part
@bp.route('/parts/<int:part_id>/<int:tag_id>', methods=['DELETE'])
def remove_part_tag(part_id, tag_id):
    try:
        part = Part.query.get_or_404(part_id)
        tag = Tag.query.get_or_404(tag_id)

        if tag not in part.tags:
            return jsonify({'error': 'Tag not associated with part'}), 404

        part.tags.remove(tag)
        db.session.commit()

        # Optionally delete tag if no longer used
        if request.args.get('delete_unused', 'false').lower() == 'true' and len(tag.parts) == 0:
            db.session.delete(tag)
            db.session.commit()
            return jsonify({'message': 'Tag removed and deleted'}), 200

        return jsonify({'message': 'Tag removed'}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400


# Get tags for specific part
@bp.route('/parts/<int:part_id>', methods=['GET'])
def get_part_tags(part_id):
    try:
        part = Part.query.options(db.joinedload(Part.tags)).get_or_404(part_id)
        return jsonify([{
            'id': tag.id,
            'name': tag.name,
            'slug': tag.slug
        } for tag in part.tags])
    except Exception as e:
        return jsonify({'error': str(e)}), 404


# Get parts with specific tag
@bp.route('/<int:tag_id>/parts', methods=['GET'])
def get_tagged_parts(tag_id):
    try:
        tag = Tag.query.options(db.joinedload(Tag.parts)).get_or_404(tag_id)
        return jsonify([{
            'id': part.id,
            'name': part.name,
            'part_number': part.part_number,
            'brand': part.brand.name if part.brand else None
        } for part in tag.parts])
    except Exception as e:
        return jsonify({'error': str(e)}), 404
