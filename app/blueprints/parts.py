from flask import Blueprint, flash, redirect, request, jsonify, current_app, \
                  render_template, url_for, abort
from slugify import slugify
from werkzeug.utils import secure_filename
from ..utils import helpers
from ..utils.helpers import admin_required, superadmin_required
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


@bp.context_processor
def inject_now():
    return {'current_year': datetime.now().year}


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@bp.route('/')
@bp.route('/gallery')
def gallery():
    # Pagination parameters
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 12, type=int)

    # Initialize query with joins for efficient sorting/filtering
    query = Part.query.join(Brand, Part.brand).options(db.joinedload(Part.brand))

    # Get all filter parameters
    brand_id = request.args.get('brand', type=int)
    part_type_id = request.args.get('type', type=int)
    search_query = request.args.get('q', '').strip()
    tags = request.args.getlist('tag')

    # Initialize filters
    filters = []
    current_filters = {
        'brand': brand_id,
        'type': part_type_id,
        'q': search_query if search_query else None
    }

    # Apply filters
    if brand_id:
        filters.append(Part.brand_id == brand_id)
    if part_type_id:
        filters.append(Part.part_type_id == part_type_id)
    if search_query:
        filters.append(or_(
            Part.name.ilike(f'%{search_query}%'),
            Part.description.ilike(f'%{search_query}%'),
            Part.part_number.ilike(f'%{search_query}%'),
            Brand.name.ilike(f'%{search_query}%')  # Include brand name in search
        ))
    if tags:
        for tag_name in tags:
            tag = Tag.query.filter_by(name=tag_name).first()
            if tag:
                filters.append(Part.tags.contains(tag))

    # Default sorting: brand name (asc) then part number (asc)
    sort = request.args.get('sort', 'brand_asc')
    if sort == 'name_asc':
        query = query.order_by(Part.name.asc())
    elif sort == 'name_desc':
        query = query.order_by(Part.name.desc())
    elif sort == 'newest':
        query = query.order_by(Part.created_at.desc())
    elif sort == 'oldest':
        query = query.order_by(Part.created_at.asc())
    else:  # Default: brand_asc
        query = query.order_by(Brand.name.asc(), Part.part_number.asc())

    # Apply filters to query
    if filters:
        query = query.filter(*filters)

    # Get paginated results
    parts = query.paginate(page=page, per_page=per_page, error_out=False)

    # Get all brands and part types for filters
    brands = Brand.query.order_by(Brand.name.asc()).all()
    part_types = PartType.query.order_by(PartType.name.asc()).all()

    # Get tags with counts
    all_tags = db.session.query(
        Tag.name,
        func.count(part_tags.c.part_id).label('count')
    ).join(part_tags).group_by(Tag.name).order_by(Tag.name.asc()).all()

    # Make sure each part has its primary image identified
    for part in parts.items:
        part.primary_image = next((img for img in part.images if img.is_primary), part.images[0] if part.images else None)

    return render_template(
        'gallery.html',
        parts=parts,
        brands=brands,
        part_types=part_types,
        all_tags=all_tags,
        current_filters=current_filters,
        per_page=per_page,
        sort=sort
    )


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
    
    
@bp.route('/add', methods=['GET', 'POST'])
@bp.route('/<int:part_id>/edit', methods=['GET', 'POST'])
@admin_required
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
                part.price_member = float(request.form.get('price_member', 0))
                part.price_non_member = float(request.form.get('price_non_member', 0))
                part.location_id = request.form.get('location_id')
                part.storage_details = request.form.get('storage_details')

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
                    price_member=float(request.form.get('price_member', 0)),
                    price_non_member=float(request.form.get('price_non_member', 0)),
                    location_id=request.form.get('location_id'),
                    storage_details=request.form.get('storage_details')
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
@admin_required
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


@bp.route('/tags/<string:tag_name>')
def parts_by_tag(tag_name):
    """Get all parts with a specific tag"""
    parts = Part.query.join(part_tags).join(Tag).filter(Tag.name == tag_name).all()
    return jsonify([p.to_dict() for p in parts])


@bp.route('/upload_images', methods=['POST'])
@admin_required
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
            'userFriendly': f' Maximum 8 images per part (already has {current_count})'
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
            if img.mode not in ['RGB', 'RGBA', 'L', 'P', '1']:  # Allowed modes
                # 'L' = grayscale, 'P' = palette, '1' = binary
                return jsonify(error="Unsupported image mode"), 400

            # Convert to RGB if needed (preserves B/W GIFs)
            if img.mode in ['L', 'P', '1']:
                img = img.convert('RGB')

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
@admin_required
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


@bp.route('/set_primary_image/<int:image_id>', methods=['POST'])
@admin_required
def set_primary_image(image_id):
    image = Image.query.get_or_404(image_id)

    try:
        # Reset current primary
        Image.query.filter_by(part_id=image.part_id, is_primary=True).update({'is_primary': False})

        # Set new primary
        image.is_primary = True
        db.session.commit()

        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@bp.route('/update_image_order', methods=['POST'])
@admin_required
def update_image_order():
    try:
        order = request.json.get('order', [])
        for index, image_id in enumerate(order):
            image = Image.query.get(image_id)
            if image:
                image.sort_order = index
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@bp.route('/add_brand', methods=['POST'])
@admin_required
def add_brand():
    try:
        data = request.get_json()
        name = data.get('name').strip()

        if not name:
            return jsonify({'success': False, 'message': 'Brand name is required'}), 400

        # Check if brand already exists
        existing_brand = Brand.query.filter(func.lower(Brand.name) == func.lower(name)).first()
        if existing_brand:
            return jsonify({
                'success': False,
                'message': f'Brand "{name}" already exists'
            }), 400

        # Create new brand with minimal required fields
        new_brand = Brand(
            name=name,
            website=data.get('website', '').strip(),
            description=data.get('description', '').strip()
        )

        db.session.add(new_brand)
        db.session.commit()

        return jsonify({
            'success': True,
            'brand': {
                'id': new_brand.id,
                'name': new_brand.name
            }
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500
