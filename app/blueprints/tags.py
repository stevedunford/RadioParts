from flask import Blueprint, render_template, request, redirect, url_for, flash
from ..models import db, Tag
from sqlalchemy.exc import IntegrityError


bp = Blueprint('tags', __name__)


@bp.route('/manage')
def manage_tags():
    """Simple tag management interface"""
    tags = Tag.query.order_by(Tag.name).all()
    return render_template('manage_tags.html', tags=tags)


@bp.route('/add', methods=['POST'])
def add_tag():
    """Add a new tag"""
    name = request.form.get('name', '').strip()
    if not name:
        flash('Tag name cannot be empty', 'error')
        return redirect(url_for('tags.manage_tags'))

    try:
        tag = Tag(name=name)
        db.session.add(tag)
        db.session.commit()
        flash(f'Tag "{name}" added successfully', 'success')
    except IntegrityError:
        db.session.rollback()
        flash(f'Tag "{name}" already exists', 'error')

    return redirect(url_for('tags.manage_tags'))


@bp.route('/edit/<int:tag_id>', methods=['POST'])
def edit_tag(tag_id):
    """Edit an existing tag"""
    tag = Tag.query.get_or_404(tag_id)
    new_name = request.form.get('name', '').strip()

    if not new_name:
        flash('Tag name cannot be empty', 'error')
        return redirect(url_for('tags.manage_tags'))

    if new_name == tag.name:
        return redirect(url_for('tags.manage_tags'))

    try:
        tag.name = new_name
        db.session.commit()
        flash('Tag updated successfully', 'success')
    except IntegrityError:
        db.session.rollback()
        flash(f'Tag "{new_name}" already exists', 'error')

    return redirect(url_for('tags.manage_tags'))


@bp.route('/delete/<int:tag_id>', methods=['POST'])
def delete_tag(tag_id):
    """Delete a tag"""
    tag = Tag.query.get_or_404(tag_id)

    try:
        db.session.delete(tag)
        db.session.commit()
        flash(f'Tag "{tag.name}" deleted successfully', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Could not delete tag: {str(e)}', 'error')

    return redirect(url_for('tags.manage_tags'))
