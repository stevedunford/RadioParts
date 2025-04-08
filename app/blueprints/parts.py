from flask import Blueprint, flash, redirect, request, jsonify, current_app, \
                  render_template, url_for, abort
from slugify import slugify
from werkzeug.utils import secure_filename
from ..utils import helpers
from ..models import db, Part, Image, PartType, Brand, Location, Tag, part_tags
from sqlalchemy import func, or_
from datetime import datetime
import os
from pathlib import Path
from PIL import Image as PILImage
from io import BytesIO


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


@bp.route('/')
def gallery():
    # Initialize query with eager loading
    query = Part.query.options(
        db.joinedload(Part.images),
        db.joinedload(Part.brand),
        db.joinedload(Part.part_type),
        db.joinedload(Part.tags)
    )

    # Filter parameters
    brand_id = request.args.get('brand', type=int)
    type_id = request.args.get('type', type=int)
    tag_names = request.args.getlist('tag')
    search_query = request.args.get('q', '').strip()

    # Apply filters
    if brand_id:
        query = query.filter_by(brand_id=brand_id)

    if type_id:
        query = query.filter_by(part_type_id=type_id)

    if tag_names:
        query = query.join(part_tags).join(Tag).filter(Tag.name.in_(tag_names))

    if search_query:
        search = f"%{search_query}%"
        query = query.filter(or_(
            Part.name.ilike(search),
            Part.description.ilike(search),
            Part.part_number.ilike(search),
            Brand.name.ilike(search),
            PartType.name.ilike(search)
        ))

    # Pagination
    page = request.args.get('page', 1, type=int)
    per_page = 12  # Items per page
    parts = query.paginate(page=page, per_page=per_page, error_out=False)

    # Get filter options
    brands = Brand.query.order_by(Brand.name).all()
    part_types = PartType.query.order_by(PartType.name).all()

      # Get all distinct tag names with their counts
    tag_counts = db.session.query(
        Tag.name,
        func.count(part_tags.c.part_id).label('count')
    ).join(
        part_tags
    ).group_by(
        Tag.name
    ).order_by(
        Tag.name
    ).all()

    # Get all tags that exist (even if unused)
    all_tags = Tag.query.order_by(Tag.name).all()

    # Combine the data
    tags_data = []
    for tag in all_tags:
        count = next((tc[1] for tc in tag_counts if tc[0] == tag.name), 0)
        tags_data.append({
            'name': tag.name,
            'count': count,
            'slug': slugify(tag.name)
        })

    return render_template(
        'gallery.html',
        parts=parts,
        brands=brands,
        part_types=part_types,
        all_tags=tags_data,  # Now passing properly structured data
        current_filters={
            'brand': brand_id,
            'type': type_id,
            'tags': tag_names,
            'q': search_query
        }
    )


@bp.route('/debug_form', methods=['POST'])
def debug_form():
    print("Form data received:", request.form.to_dict())
    print("Files received:", request.files.to_dict())
    return jsonify(request.form.to_dict())


@bp.route('/add', methods=['GET', 'POST'])
@bp.route('/<int:part_id>/edit', methods=['GET', 'POST'])
def manage_part(part_id=None):
    part = Part.query.get(part_id) if part_id else None

    brands = Brand.query.order_by(Brand.name).all()
    part_types = PartType.query.order_by(PartType.name).all()
    locations = Location.query.order_by(Location.name).all()
    all_tags = Tag.query.order_by(Tag.name).all()

    if request.method == 'POST':
        try:
            # Start a transaction
            db.session.begin_nested()

            if part:
                print(f"Existing part id {part.id} being updated")
                # Update existing part
                part.name = request.form.get('name')
                part.description = request.form.get('description')
                part.part_number = request.form.get('part_number')
                part.brand_id = request.form.get('brand_id')
                part.part_type_id = request.form.get('part_type_id')
                part.location_id = request.form.get('location_id')
                part.box = request.form.get('box')
                part.position = request.form.get('position')

                # Handle deleted images
                deleted_images = request.form.get('deleted_images', '').split(',')
                for image_id in deleted_images:
                    if image_id:
                        image = Image.query.get(int(image_id))
                        if image:
                            db.session.delete(image)

                # Handle tags - clear existing first
                part.tags.clear()
                for tag_name in request.form.getlist('tags[]'):
                    tag = Tag.query.filter(func.lower(Tag.name) == func.lower(tag_name)).first()
                    if not tag:
                        tag = Tag(name=tag_name)
                        db.session.add(tag)
                    part.tags.append(tag)

                # Update part in database
                db.session.commit()

            else:
                # Create new part
                print("Creating a new part")
                part = Part(
                    name=request.form.get('name'),
                    description=request.form.get('description'),
                    part_number=request.form.get('part_number'),
                    brand_id=request.form.get('brand_id'),
                    part_type_id=request.form.get('part_type_id'),
                    location_id=request.form.get('location_id'),
                    box=request.form.get('box'),
                    position=request.form.get('position')
                )
                print("Adding part to db")
                db.session.add(part)
                print("Flush changes to db")
                db.session.flush()  # Get the ID before commit
                print(f"should have id: {part.id}")

                # Handle tags for new part
                for tag_name in request.form.getlist('tags[]'):
                    tag = Tag.query.filter(func.lower(Tag.name) == func.lower(tag_name)).first()
                    if not tag:
                        tag = Tag(name=tag_name)
                        db.session.add(tag)
                    part.tags.append(tag)

            # Handle image associations
            image_ids = request.form.getlist('image_ids[]')
            print("Received image IDs:", request.form.getlist('image_ids[]'))
            for image_id in image_ids:
                if image_id:  # Skip empty strings
                    image = Image.query.get(int(image_id))
                    if image and image not in part.images:
                        part.images.append(image)
                        # Ensure the image has the correct part_id
                        image.part_id = part.id

            db.session.commit()
            print("Committed changes successfully")

            # New response handling logic:
            response_data = {
                'success': True,
                'part_id': part.id,
                'message': 'Part saved successfully',
                'redirect': url_for('parts.view_part', part_id=part.id)
            }

            if request.accept_mimetypes.accept_json or 'application/json' in request.headers.get('Accept', ''):
                return jsonify(response_data), 200, {'Content-Type': 'application/json'}

            flash(response_data['message'], 'success')
            return redirect(response_data['redirect'])

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error saving part: {str(e)}")

            error_response = {
                'success': False,
                'message': f'Error saving part: {str(e)}'
            }

            if request.accept_mimetypes.accept_json or 'application/json' in request.headers.get('Accept', ''):
                return jsonify(error_response), 400, {'Content-Type': 'application/json'}

            flash(error_response['message'], 'error')
            return redirect(request.url)

    return render_template('manage_part.html',
                           part=part,
                           brands=brands,
                           part_types=part_types,
                           locations=locations,
                           all_tags=all_tags)


@bp.route('/<int:part_id>/delete', methods=['POST'])
def delete_part(part_id):
    part = Part.query.get_or_404(part_id)
    try:
        # Delete associated images from filesystem
        for image in part.images:
            image_path = Path(current_app.config['UPLOAD_FOLDER']) / image.filename
            if image_path.exists():
                image_path.unlink()

        # Delete from database (tags are handled via cascade)
        db.session.delete(part)
        db.session.commit()

        return jsonify({
            'success': True,
            'redirect': url_for('parts.gallery')
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@bp.route('/<int:part_id>')
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


@bp.route('/tags/<string:tag_name>')
def parts_by_tag(tag_name):
    """Get all parts with a specific tag"""
    parts = Part.query.join(part_tags).join(Tag).filter(Tag.name == tag_name).all()
    return jsonify([p.to_dict() for p in parts])


@bp.route('/upload_images', methods=['POST'])
def upload_images():
    print("-- Uploading images --")
    print("Received CSRF Token:", request.headers.get('X-CSRF-Token'))
    print("Form CSRF Token:", request.form.get('csrf_token'))
    print(request.files)  # Debug what's actually received
    """Handle file uploads with image processing"""
    if 'file' not in request.files:  # Changed from 'files' to 'file'
        return jsonify(error="No files uploaded"), 400
    
    part_id = request.form.get('part_id')
    part = Part.query.get(part_id) if part_id else None
    upload_dir = Path(current_app.config['UPLOAD_FOLDER'])
    upload_dir.mkdir(parents=True, exist_ok=True)

    # Enforce 8-image limit
    current_count = len(part.images) if part else 0
    if current_count >= 8:
        return jsonify({
            'error': 'You can only have 8 images per part',
            'message': 'Maximum 8 images allowed',
            'userFriendly': '❌ Maximum 8 images per part (already has {current_count})'
        }), 400
   
    # Get single file (FilePond sends one at a time)
    file = request.files['file']  # Changed from getlist('files')
    responses = []

    # Remove the file iteration loop since we handle one file
    if file and file.filename != '':
        try:
            if not allowed_file(file.filename):
                return jsonify(error="Invalid file type"), 400
                
            filename = secure_filename(file.filename)
            save_path = upload_dir / filename

            # Process image
            img = PILImage.open(file.stream)
            
            # Resize if needed (maintain aspect ratio)
            if img.width > 1200 or img.height > 1200:
                img.thumbnail((1200, 1200))
            
            # Save with quality compression
            buffer = BytesIO()
            img.save(buffer, format='JPEG', quality=70)
            buffer.seek(0)
            
            # Handle duplicates
            counter = 1
            while save_path.exists():
                name, ext = os.path.splitext(filename)
                filename = f"{name}_{counter}.jpg"  # Force JPG extension
                save_path = upload_dir / filename
                counter += 1

            with open(save_path, 'wb') as f:
                f.write(buffer.getvalue())

            new_image = Image(
                filename=filename,
                part_id=part.id if part else None
            )
            db.session.add(new_image)
            db.session.flush()

            response = {
                "id": new_image.id,
                "name": filename,
                "url": url_for('static', filename=f"images/{filename}"),
                "size": save_path.stat().st_size
            }
            responses.append(response)
            db.session.commit()

        except Exception as e:
            db.session.rollback()
            return jsonify({
                'error': 'processing_error',
                'message': str(e),
                'userFriendly': '❌ Failed to process image'
            }),     500

    return jsonify(response), 201  # Return single response
    #   return jsonify(responses[0] if len(responses) == 1 else responses), 201


@bp.route('/delete_image/<int:image_id>', methods=['DELETE'])
def delete_image(image_id):
    image = Image.query.get_or_404(image_id)
    try:
        image_path = Path(current_app.config['UPLOAD_FOLDER']) / image.filename
        if image_path.exists():
            image_path.unlink()
        db.session.delete(image)
        db.session.commit()
        return jsonify({"success": True, "message": "Image deleted"})  # Explicit JSON response
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500
