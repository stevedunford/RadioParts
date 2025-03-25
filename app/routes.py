from app import app
from flask import flash, redirect, render_template, request, jsonify, \
                  send_from_directory, url_for
from flask_sqlalchemy import SQLAlchemy
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
        tag = models.Tag.query.filter_by(name=tag_filter).first_or_404()
        images = tag.images
    else:
        images = models.Image.query.all()

    all_tags = models.Tag.query.all()
    return render_template('gallery.html', images=images, all_tags=all_tags)


@app.route('/uploader')
def uploader():
    images = models.Image.query.all()
    return render_template('upload.html', images=images)


@app.route('/upload', methods=['POST'])
def upload():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    # Save the file
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
    file.save(file_path)

    # Save the image details to the database
    # with a default empty description
    image = models.Image(filename=file.filename, description='')
    db.session.add(image)
    db.session.commit()

    return jsonify({'message': 'File uploaded successfully',
                    'filename': file.filename,
                    'id': image.id}), 200


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
    return render_template('edit_image.html', image=image)


@app.route('/add_tag/<int:image_id>', methods=['POST'])
def add_tag(image_id):
    tag_name = request.json.get('tag')
    if not tag_name:
        return jsonify({'error': 'Tag name is required'}), 400

    # Find or create the tag
    tag = models.Tag.query.filter_by(name=tag_name).first()
    if not tag:
        tag = models.Tag(name=tag_name)
        db.session.add(tag)
        db.session.commit()

    # Associate the tag with the image
    image = models.Image.query.get(image_id)
    if not image:
        return jsonify({'error': 'Image not found'}), 404

    if tag not in image.tags:
        image.tags.append(tag)
        db.session.commit()

    return jsonify({'message': 'Tag added successfully'}), 200


@app.route('/delete/<int:image_id>', methods=['POST'])
def delete_image(image_id):
    image = models.Image.query.get(image_id)
    if not image:
        return jsonify({'error': 'Image not found'}), 404

    # Delete the file from the filesystem
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], image.name)
    if os.path.exists(file_path):
        os.remove(file_path)

    # Delete the image from the database
    db.session.delete(image)
    db.session.commit()

    return jsonify({'message': 'File deleted successfully'}), 200


@app.route('/tag-manager')
def tag_manager():
    all_tags = models.Tag.query.order_by(models.Tag.name).all()
    return render_template('tag_manager.html', all_tags=all_tags)


#################################
# API Routes for Tag Management #
#################################

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


@app.route('/api/tags/merge', methods=['POST'])
def merge_tags():
    source_ids = request.json.get('source_ids', [])
    target_id = request.json.get('target_id')

    if not source_ids or not target_id:
        return jsonify({'error': 'Source and target tags required'}), 400

    target_tag = models.Tag.query.get_or_404(target_id)

    # Get all images with source tags
    for source_id in source_ids:
        if source_id == target_id:
            continue

        source_tag = models.Tag.query.get_or_404(source_id)
        for image in source_tag.images:
            if target_tag not in image.tags:
                image.tags.append(target_tag)
        db.session.delete(source_tag)

    db.session.commit()
    return jsonify({'message': f'Merged {len(source_ids)} \
                    tags into {target_tag.name}'})


if __name__ == '__main__':
    app.run(debug=True)
