from app import app
from flask import flash, redirect, render_template, request, jsonify, \
                  send_from_directory, url_for
from werkzeug.utils import secure_filename
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func, insert
import os
# import secrets
# print(secrets.token_hex(32))


app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///nzvintageradioparts.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'app/static/images'
app.config['SECRET_KEY'] = '5ef4c1b869eb15c48956292bb37b7115\
                            cac26ba71f5d5be7ce3d9fc16d8a4e23'
db = SQLAlchemy(app)

# Ensure the upload folder exists
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

# Import models (if they're in a separate file)
import app.models as models  # NOQA


# Debugging - check images are being served correctly
@app.route('/static/images/<path:filename>')
def serve_static(filename):
    print(f"Attempting to serve: static/images/{filename}")  # Debug output
    return send_from_directory('static/images', filename)


@app.route('/')
def index():
    images = models.Image.query.all()
    return render_template('home.html', images=images)


@app.route('/gallery')
def gallery():
    tag_filter = request.args.get('tag')
    
    if tag_filter:
        # Get tag with image count
        tag = db.session.query(
            models.Tag,
            db.func.count(models.ImageTag.iid).label('image_count')
        ).join(
            models.ImageTag,
            models.Tag.id == models.ImageTag.tid
        ).filter(models.Tag.name == tag_filter).group_by(models.Tag.id).first_or_404()
        
        images = tag[0].images.all()  # Explicitly execute the query
    else:
        images = models.Image.query.all()
    
    # Get all tags with counts
    all_tags = db.session.query(
        models.Tag,
        db.func.count(models.ImageTag.iid).label('image_count')
    ).outerjoin(
        models.ImageTag,
        models.Tag.id == models.ImageTag.tid
    ).group_by(models.Tag.id).all()
    
    return render_template('gallery.html',
                           images=images,
                           all_tags=all_tags,
                           current_tag=tag_filter)


@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if request.method == 'POST':
        # Check if files were submitted
        if 'images' not in request.files:
            flash('No files selected', 'error')
            return redirect(request.url)
            
        files = request.files.getlist('images')
        uploaded_files = []
        
        for file in files:
            # Skip if no file selected
            if file.filename == '':
                continue
                
            # Validate file
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                
                # Handle duplicate filenames
                save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                counter = 1
                while os.path.exists(save_path):
                    name, ext = os.path.splitext(filename)
                    filename = f"{name}_{counter}{ext}"
                    save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    counter += 1
                
                # Save file
                file.save(save_path)
                
                # Create database record
                new_image = models.Image(filename=filename)
                db.session.add(new_image)
                uploaded_files.append(filename)
        
        if uploaded_files:
            db.session.commit()
            flash(f'{len(uploaded_files)} files uploaded successfully', 'success')
        else:
            flash('No valid files uploaded', 'warning')
            
        return redirect(url_for('upload'))
    
    # GET request - show upload page
    images = models.Image.query.order_by(models.Image.created_at.desc()).all()
    return render_template('upload.html', images=images)


@app.route('/update/<int:image_id>', methods=['POST'])
def update_image(image_id):
    image = models.Image.query.get_or_404(image_id)

    # Update description
    image.description = request.form.get('description', '')

    # Update tags
    tag_names = [t.strip()
                 for t in request.form.get('tags', '').split(',')
                 if t.strip()]
    image.tags = []
    for tag_name in tag_names:
        tag = models.Tag.query.filter_by(name=tag_name).first()
        if not tag:
            tag = models.Tag(name=tag_name)
            db.session.add(tag)
        image.tags.append(tag)

    db.session.commit()
    flash('Image updated successfully!', 'success')
    return redirect(url_for('gallery'))


@app.route('/update_description/<int:image_id>', methods=['POST'])
def update_description(image_id):
    description = request.json.get('description')
    if not description:
        return jsonify({'error': 'Description is required'}), 400

    image = models.Image.query.get(image_id)
    if not image:
        return jsonify({'error': 'Image not found'}), 404

    image.description = description
    db.session.commit()

    return jsonify({'message': 'Description updated successfully'}), 200


@app.route('/edit/<int:image_id>')
def edit_image(image_id):
    image = models.Image.query.get_or_404(image_id)
    all_tags = models.Tag.query.with_entities(models.Tag.name).distinct().all()
    return render_template('edit_image.html', image=image,
                           all_tags=[tag[0] for tag in all_tags])


@app.route('/add_tag/<int:image_id>', methods=['POST'])
def add_tag(image_id):
    data = request.get_json()
    tag_name = data['tag'].strip().lower()  # Normalize to lowercase

    # Validate
    if len(tag_name) > 20:
        return jsonify(error="Tag too long (max 20 chars)"), 400

    image = models.Image.query.get_or_404(image_id)

    # Check tag limit
    if image.tags.count() >= 8:  # Using .count() for many-to-many
        return jsonify(error="Maximum 8 tags per image"), 400

    # Find or create tag (case-insensitive)
    existing_tag = models.Tag.query.filter(func.lower(models.Tag.name) == tag_name).first()

    if existing_tag:
        # Check if image already has this tag
        if existing_tag in image.tags:
            return jsonify(error=f"Tag '{tag_name}' already exists"), 400
    else:
        existing_tag = models.Tag(name=tag_name.capitalize())  # Store with capitalization
        db.session.add(existing_tag)

    # Add association
    db.session.execute(
        insert(models.ImageTag).values(iid=image_id, tid=existing_tag.id)
    )
    db.session.commit()

    return jsonify(
        success=True,
        tag=existing_tag.name,
        tag_id=existing_tag.id
    )


# Edit Tag Page (GET for form, POST for submission)
@app.route('/tags/<int:tag_id>/edit', methods=['GET', 'POST'])
def edit_tag(tag_id):
    tag = models.Tag.query.get_or_404(tag_id)
    
    if request.method == 'POST':
        new_name = request.form.get('name')
        
        # Validation
        if not new_name:
            flash('Tag name is required', 'error')
        elif models.Tag.query.filter(models.Tag.id != tag_id,
                                     models.Tag.name == new_name).first():
            flash('Tag name already in use', 'error')
        else:
            tag.name = new_name
            db.session.commit()
            flash('Tag updated successfully', 'success')
            return redirect(url_for('tag_manager'))
        
    return render_template('edit_tag.html', tag=tag)


@app.route('/tag_manager')
def tag_manager():
    page = request.args.get('page', 1, type=int)
    per_page = 20

    # Modified query to return (Tag, count) pairs
    tags_query = db.session.query(
        models.Tag,
        db.func.count(models.ImageTag.iid).label('image_count')
    ).outerjoin(
        models.ImageTag,
        models.Tag.id == models.ImageTag.tid
    ).group_by(models.Tag.id)

    # Apply search filter if exists
    if 'search' in request.args:
        search_term = f"%{request.args['search']}%"
        tags_query = tags_query.filter(models.Tag.name.ilike(search_term))

    # Apply sorting
    sort_by = request.args.get('sort', 'name')
    if sort_by == 'count':
        tags_query = tags_query.order_by(db.desc('image_count'))
    else:
        tags_query = tags_query.order_by(models.Tag.name)

    # Get paginated results
    paginated_tags = tags_query.paginate(page=page, per_page=per_page)

    # Convert to dictionary for easier template access
    tags = [{
        'tag': tag,
        'count': count,
        'samples': tag.get_associated_images(3).all()  # Now calling on Tag instance
    } for tag, count in paginated_tags.items]

    return render_template('tag_manager.html',
                           tags=tags,
                           pagination=paginated_tags,
                           current_sort=sort_by,
                           search_term=request.args.get('search', ''))


############################################
# API Routes for Upload and Tag Management #
############################################

@app.route('/api/upload', methods=['POST'])
def api_upload():
    """AJAX endpoint for file uploads"""
    if 'images' not in request.files:
        return jsonify({'error': 'No files selected'}), 400
        
    files = request.files.getlist('images')
    if not files or all(f.filename == '' for f in files):
        return jsonify({'error': 'No valid files selected'}), 400
    
    uploaded_files = []
    
    for file in files:
        if file.filename == '':
            continue
            
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            
            # Handle duplicates
            counter = 1
            while os.path.exists(save_path):
                name, ext = os.path.splitext(filename)
                filename = f"{name}_{counter}{ext}"
                save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                counter += 1
            
            file.save(save_path)
            new_image = models.Image(filename=filename)
            db.session.add(new_image)
            uploaded_files.append({
                'filename': filename,
                'url': url_for('static', filename=f'images/{filename}', _external=True)
            })
    
    if uploaded_files:
        db.session.commit()
        return jsonify({
            'success': True,
            'files': uploaded_files,
            'message': f'Uploaded {len(uploaded_files)} files'
        }), 200  # Explicit status code
    else:
        return jsonify({'error': 'No valid files processed'}), 400


@app.route('/api/images/<int:image_id>', methods=['DELETE'])
def delete_image(image_id):
    """Delete an image"""
    image = models.Image.query.get_or_404(image_id)
    
    # Delete file from filesystem
    try:
        os.remove(os.path.join(app.config['UPLOAD_FOLDER'], image.filename))
    except FileNotFoundError:
        pass  # Already deleted or never existed
    
    # Delete from database
    db.session.delete(image)
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Image deleted'})


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
    

@app.route('/api/tags', methods=['POST'])
def create_tag():
    name = request.json.get('name')
    if not name:
        return jsonify({'error': 'Tag name is required'}), 400

    if models.Tag.query.filter_by(name=name).first():
        return jsonify({'error': 'Tag already exists'}), 400

    tag = models.Tag(name=name)
    db.session.add(tag)
    db.session.commit()
    return jsonify({'message': 'Tag created'}), 201


@app.route('/api/tags/<int:tag_id>', methods=['PUT'])
def update_tag(tag_id):
    tag = models.Tag.query.get_or_404(tag_id)
    new_name = request.json.get('name')

    if not new_name:
        return jsonify({'error': 'New name is required'}), 400

    if models.Tag.query.filter(models.Tag.id != tag_id,
                               models.Tag.name == new_name).first():
        return jsonify({'error': 'Tag name already in use'}), 400

    tag.name = new_name
    db.session.commit()
    return jsonify({'message': 'Tag updated'})


@app.route('/api/tags/<int:tag_id>', methods=['DELETE'])
def delete_tag(tag_id):
    tag = models.Tag.query.get_or_404(tag_id)
    db.session.delete(tag)
    db.session.commit()
    return jsonify({'message': 'Tag deleted'})


# Tag merging endpoint
@app.route('/tags/<int:source_id>/merge_into/<int:target_id>', methods=['POST'])
def merge_tags(source_id, target_id):
    source_tag = models.Tag.query.get_or_404(source_id)
    target_tag = models.Tag.query.get_or_404(target_id)
    source_tag.merge_into(target_tag)
    return jsonify(success=True)


# Tag search API
@app.route('/api/tags/search')
def tag_search_api():
    query = request.args.get('q', '')
    tags = models.Tag.query.filter(models.Tag.name.ilike(f'%{query}%')).limit(10).all()
    return jsonify([{'id': t.id, 'text': t.name} for t in tags])


if __name__ == '__main__':
    app.run(debug=True)
