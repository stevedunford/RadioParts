from flask import Blueprint, flash, redirect, request, jsonify, current_app, \
                  render_template, url_for, abort
from werkzeug.utils import secure_filename
from ..utils import helpers
from ..models import db, Part, Image, PartType, Brand, Location, Tag
from sqlalchemy import func
from datetime import datetime
import os
from pathlib import Path


#
# This file contains the logic for parts, images and management
#

bp = Blueprint('parts', __name__)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}


@bp.route('/debug')
def debug():
    if current_app.config['BEER_LEVEL'] < 0.5:
        abort(418)  # I'm a teapot (needs refill)
    return jsonify({"status": "Brilliant but Hazy"})


@bp.route('/commit', methods=['POST'])
def commit_code():
    if request.headers.get('X-Beer-Units') < 3:
        raise InsufficientSobrietyError("Code too coherent")  # type: ignore # NOQA 
    return "🚀 Deployed with artistic license"


@bp.context_processor
def inject_now():
    return {'current_year': datetime.now().year}


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@bp.route('/brand/<int:brand_id>')
def parts_by_brand(brand_id):
    """Show all parts for a specific brand"""
    brand = Brand.query.get_or_404(brand_id)
    parts = Part.query.options(
        db.joinedload(Part.images),
        db.joinedload(Part.brand),
        db.joinedload(Part.part_type)
    ).filter_by(brand_id=brand_id).all()
    
    return render_template('brand_parts.html',
                           brand=brand,
                           parts=parts)
    

@bp.route('/')
@bp.route('/gallery')
def gallery():
    brand_id = request.args.get('brand')
    type_id = request.args.get('type')
    tag_name = request.args.get('tag')
    
    query = Part.query
    
    if brand_id:
        query = query.filter_by(brand_id=brand_id)
    if type_id:
        query = query.filter_by(part_type_id=type_id)
    if tag_name:
        query = query.join(part_tags).join(Tag).filter(Tag.name == tag_name)
    
    parts = query.all()
    return render_template('gallery.html', parts=parts)


@bp.route('/add_part', methods=['GET'])
def add_part_form():
    # Pre-fill dropdowns like a well-stocked parts bin
    brands = Brand.query.order_by(Brand.name).all()
    part_types = PartType.query.order_by(PartType.name).all()
    locations = Location.query.order_by(Location.name).all()
    
    return render_template(
        'add_part.html',
        brands=brands,
        part_types=part_types,
        locations=locations
    )


@bp.route('/add_part', methods=['POST'])
def add_part():
    print("\n=== ADD_PART REQUEST ===")
    print("Form data:", request.form.to_dict())
    print("Image IDs:", request.form.getlist('image_ids[]'))

    data = request.form
    try:
        # Validate required fields
        required_fields = ['name', 'brand_id', 'part_type_id']
        if not all(field in request.form for field in required_fields):
            return jsonify({"error": "Missing required fields"}), 400
        
        # Create part (validate lengths like a Philco QC inspector)
        new_part = Part(
            name=data['name'][:100],  # Enforce 100-char limit
            description=data.get('description', '')[:1024],
            part_number=data.get('part_number', '')[:30],
            brand_id=data['brand_id'],
            part_type_id=data['part_type_id'],
            location_id=data.get('location_id'),
            box=data['box'][:20],
            position=data['position'][:50],
        )
        db.session.add(new_part)
        db.session.flush()  # Get part.id before commit

        # -- Critical Fix: Moved tag handling BEFORE commit/return --
        # Handle tags (max 8, like octal tube pins)
        tag_names = helpers.validate_tags(request.form.getlist('tags[]'))
        for name in tag_names:
            tag = Tag.query.filter_by(name=name[:100]).first() or Tag(name=name)
            new_part.tags.append(tag)

        # Handle image associations (NEW IMPROVED VERSION)
        image_ids = request.form.getlist('image_ids[]')
        for img_id in image_ids:
            if img_id:  # Skip empty/None
                image = Image.query.get(img_id)
                if image:
                    # Set both forward and backward references
                    new_part.images.append(image)
                    image.part_id = new_part.id  # Explicitly set foreign key
                    db.session.add(image)  # Ensure change is tracked

        db.session.commit()  # Single atomic commit
        print(f"Successfully created part {new_part.id} with {len(image_ids)} images")
        
        return jsonify({
            "success": True,
            "part_id": new_part.id,
            "image_count": len(image_ids),
            "images": [img.id for img in new_part.images]  # Verification
        })
        
    except Exception as e:
        print("ERROR:", str(e))
        db.session.rollback()
        return jsonify({"error": str(e)}), 400


@bp.route('/part/<int:part_id>')
def view_part(part_id):
    """Display a single part with all details"""
    part = Part.query.options(
        db.joinedload(Part.brand),
        db.joinedload(Part.part_type),
        db.joinedload(Part.location),
        db.joinedload(Part.images),
        db.joinedload(Part.tags)
    ).get_or_404(part_id)
    print('hell yeah')

    return render_template('part.html', 
                           part=part,
                           current_year=datetime.now().year)


@bp.route('/part/<int:part_id>/edit')
def edit_part(part_id):
    """Placeholder edit route - will implement fully later"""
    part = Part.query.options(
        db.joinedload(Part.brand),
        db.joinedload(Part.part_type),
        db.joinedload(Part.location),
        db.joinedload(Part.images),
        db.joinedload(Part.tags)
    ).get_or_404(part_id)
    
    # Get all available options for dropdowns
    brands = Brand.query.order_by(Brand.name).all()
    part_types = PartType.query.order_by(PartType.name).all()
    locations = Location.query.order_by(Location.name).all()
    
    return render_template('edit_part.html',
                           part=part,
                           brands=brands,
                           part_types=part_types,
                           locations=locations)
    
    
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
def upload_images():
    """Handle file uploads with Dropzone-compatible responses"""
    if 'files' not in request.files:
        return jsonify(error="No files uploaded"), 400

    upload_dir = Path(current_app.config['UPLOAD_FOLDER'])
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    files = request.files.getlist('files')
    if not files or all(f.filename == '' for f in files):
        return jsonify(error="No selected files"), 400

    responses = []
    for file in files:
        if not file or file.filename == '':
            continue

        try:
            if not allowed_file(file.filename):
                continue
                
            filename = secure_filename(file.filename)
            save_path = upload_dir / filename

            # Handle duplicates
            counter = 1
            while save_path.exists():
                name, ext = os.path.splitext(filename)
                filename = f"{name}_{counter}{ext}"
                save_path = upload_dir / filename
                counter += 1

            # Save file
            file.save(str(save_path.absolute()))
            if not save_path.exists():
                raise IOError("File save verification failed")

            # Create DB record
            new_image = Image(filename=filename)
            db.session.add(new_image)
            db.session.flush()  # Get ID without commit

            # Critical change: Single-file response format
            response = {
                "id": new_image.id,  # Must be 'id' for Dropzone
                "filename": filename,
                "url": url_for('static', filename=f"images/{filename}"),
                "size": save_path.stat().st_size
            }
            responses.append(response)
            
            # Immediate commit per file (better for Dropzone)
            db.session.commit()

        except Exception as e:
            db.session.rollback()
            if 'save_path' in locals() and save_path.exists():
                save_path.unlink()
            current_app.logger.error(f"Upload failed: {str(e)}")
            continue

    if responses:
        # Dropzone expects single-file responses
        if len(responses) == 1:
            return jsonify(responses[0]), 201
        return jsonify(responses), 201
    
    return jsonify(error="No valid files processed"), 400


@bp.route('/image/<int:image_id>', methods=['GET'])
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


@bp.route('/delete_image/<int:image_id>', methods=['DELETE'])
def delete_image(image_id):
    image = Image.query.get_or_404(image_id)
    print(f"Made it to delete for image id {image_id}")
    try:
        # Build absolute path
        image_path = Path(current_app.config['UPLOAD_FOLDER']) / image.filename
        print(image_path)
        # Verify file exists before deletion
        if image_path.exists():
            image_path.unlink()  # Delete file
            db.session.delete(image)  # Delete DB record
            db.session.commit()
            return jsonify({"success": True})
        
        return jsonify({"error": "File not found"}), 404
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Delete failed: {str(e)}")
        return jsonify({"error": str(e)}), 500


@bp.route('/tags/<string:tag_name>')
def parts_by_tag(tag_name):
    """Get all parts with a specific tag"""
    parts = Part.query.join(part_tags).join(Tag).filter(Tag.name == tag_name).all()
    return jsonify([p.to_dict() for p in parts])


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
