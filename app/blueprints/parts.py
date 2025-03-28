from flask import Blueprint, flash, redirect, request, jsonify, current_app, render_template, url_for
from werkzeug.utils import secure_filename
from ..models import db, Image, Tag
from sqlalchemy import func
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import os


#
# This file contains the logic for parts, images and management
#

bp = Blueprint('images', __name__)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}


@bp.app_template_filter('nztime')
def convert_to_nz_time(dt):
    """Convert UTC datetime to NZ time"""
    if dt.tzinfo is None:  # Handle naive datetimes
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(ZoneInfo("Pacific/Auckland"))


@bp.context_processor
def inject_now():
    return {'current_year': datetime.now().year}


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@bp.route('/')
@bp.route('/gallery')
def gallery():
    """Display all images in a gallery view"""
    images = Image.query.options(db.joinedload(Image.tags)).all()
    return render_template('gallery.html', images=images)


@bp.route('/<int:image_id>/edit')
def edit_image(image_id):
    image = Image.query.get_or_404(image_id)
    all_tags = Tag.query.order_by(Tag.name).all()  # Get ALL tags from database
    return render_template('edit.html', 
                         image=image,
                         image_tags=image.tags,  # Just the tags on this image
                         all_tags=all_tags)      # All possible tags


@bp.route('/all_images', methods=['GET'])
def get_images():
    """Get all images with their tags"""
    images = Image.query.options(db.joinedload(Image.tags)).all()
    return jsonify([{
        'id': img.id,
        'filename': img.filename,
        'description': img.description,
        'created_at': img.created_at.isoformat(),
        'tags': [{'id': t.id, 'name': t.name} for t in img.tags],
        'url': f"/static/images/{img.filename}"
    } for img in images])

@bp.route('/upload_images', methods=['POST'])
def upload_image():
    """Handle single or multiple image uploads"""
    if 'files' not in request.files:
        return jsonify(error="No files uploaded"), 400

    files = request.files.getlist('files')
    if not files or all(f.filename == '' for f in files):
        return jsonify(error="No selected files"), 400

    uploads = []
    for file in files:
        if file.filename == '':
            continue

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            save_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)

            # Handle duplicates
            counter = 1
            while os.path.exists(save_path):
                name, ext = os.path.splitext(filename)
                filename = f"{name}_{counter}{ext}"
                save_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
                counter += 1

            file.save(save_path)
            new_image = Image(filename=filename)
            db.session.add(new_image)
            uploads.append({
                'id': new_image.id,
                'filename': filename,
                'url': f"/static/images/{filename}"
            })

    if uploads:
        db.session.commit()
        return jsonify(uploads), 201
    return jsonify(error="No valid files processed"), 400


@bp.route('/<int:image_id>', methods=['GET'])
def get_image(image_id):
    """Get single image details"""
    image = Image.query.options(db.joinedload(Image.tags)).get_or_404(image_id)
    return jsonify({
        'id': image.id,
        'filename': image.filename,
        'description': image.description,
        'created_at': image.created_at.isoformat(),
        'tags': [{'id': t.id, 'name': t.name} for t in image.tags],
        'url': f"/static/images/{image.filename}"
    })


@bp.route('/<int:image_id>/update', methods=['POST'])
def update_image(image_id):
    image = Image.query.get_or_404(image_id)
    image.description = request.form.get('description', '')[:500]  # Truncate to 500 chars
    db.session.commit()
    flash('Image updated successfully!', 'success')
    return redirect(url_for('images.gallery'))


@bp.route('/<int:image_id>', methods=['DELETE'])
def delete_image(image_id):
    """Delete an image and its tag associations"""
    image = Image.query.get_or_404(image_id)
    
    try:
        # Delete file from filesystem
        file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], image.filename)
        if os.path.exists(file_path):
            os.remove(file_path)
            
        # Delete from database
        db.session.delete(image)
        db.session.commit()
        return jsonify(message="Image deleted")
    except Exception as e:
        db.session.rollback()
        return jsonify(error=str(e)), 500


@bp.route('/<int:image_id>/tags', methods=['GET'])
def get_image_tags(image_id):
    """Get tags for a specific image"""
    image = Image.query.options(db.joinedload(Image.tags)).get_or_404(image_id)
    return jsonify([{
        'id': tag.id,
        'name': tag.name
    } for tag in image.tags])


@bp.route('/<int:image_id>/tags', methods=['POST'])
def add_image_tag(image_id):
    """Add tag to image (creates tag if new)"""
    data = request.get_json()
    if not data or 'name' not in data:
        return jsonify(error="Tag name required"), 400
        
    tag_name = data['name'].strip().lower()
    if not tag_name:
        return jsonify(error="Empty tag name"), 400
    if len(tag_name) > 20:
        return jsonify(error="Tag too long (max 20 chars)"), 400

    image = Image.query.get_or_404(image_id)
    
    # Check if already tagged
    if any(t.name.lower() == tag_name for t in image.tags):
        return jsonify(error="Image already has this tag"), 400
        
    # Check tag limit
    if len(image.tags) >= 8:
        return jsonify(error="Maximum 8 tags per image"), 400

    # Find or create tag
    tag = Tag.query.filter(func.lower(Tag.name) == tag_name).first()
    is_new = False
    
    if not tag:
        tag = Tag(name=tag_name.capitalize())
        db.session.add(tag)
        is_new = True
    
    image.tags.append(tag)
    db.session.commit()
    
    return jsonify({
        'id': tag.id,
        'name': tag.name,
        'is_new': is_new
    }), 201 if is_new else 200


@bp.route('/<int:image_id>/tags/<int:tag_id>/add', methods=['POST'])
def add_tag(image_id, tag_id):
    # Check if association already exists
    if not db.session.query(ImageTag).filter_by(iid=image_id, tid=tag_id).first():
        association = ImageTag(iid=image_id, tid=tag_id)
        db.session.add(association)
        db.session.commit()
    return jsonify({'status': 'success'})


@bp.route('/<int:image_id>/tags/<int:tag_id>/remove', methods=['POST'])
def remove_tag(image_id, tag_id):
    association = db.session.query(ImageTag).filter_by(
        iid=image_id, tid=tag_id
    ).first_or_404()
    db.session.delete(association)
    db.session.commit()
    return jsonify({'status': 'success'})


@bp.route('/images/<int:image_id>/tags/available')
def available_tags(image_id):
    image = Image.query.get_or_404(image_id)
    all_tags = Tag.query.order_by(Tag.name).all()
    available = [tag for tag in all_tags if tag not in image.tags]
    return jsonify([{'id': tag.id, 'name': tag.name} for tag in available])
