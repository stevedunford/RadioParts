from sqlalchemy import func, Index, update
from datetime import datetime
from app.routes import db


class Image(db.Model):
    __tablename__ = 'Image'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    filename = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    tags = db.relationship('Tag',
                           secondary='ImageTag',
                           backref=db.backref('images', lazy='dynamic'))


class Tag(db.Model):
    __tablename__ = 'Tag'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), nullable=False, unique=True)

    # Case-insensitive index
    __table_args__ = (
        Index('idx_tag_name_lower', func.lower(name)),
    )
    
    @property
    def image_count(self):
        """Get count of associated images without loading them all"""
        from sqlalchemy import func
        return db.session.query(func.count(ImageTag.iid))\
            .filter_by(tid=self.id).scalar()

    def get_associated_images(self, limit=None):
        """Get query for associated images with optional limit"""
        query = Image.query.join(ImageTag).filter(ImageTag.tid == self.id)
        return query.limit(limit) if limit else query

    def merge_into(self, target_tag):
        """Merge this tag into another tag"""
        # Update all ImageTag associations
        db.session.execute(
            update(ImageTag)
            .where(ImageTag.tid == self.id)
            .values(tid=target_tag.id)
        )
        db.session.delete(self)
        db.session.commit()


class ImageTag(db.Model):
    __tablename__ = 'ImageTag'
    iid = db.Column(db.Integer, db.ForeignKey('Image.id'), primary_key=True)
    tid = db.Column(db.Integer, db.ForeignKey('Tag.id'), primary_key=True)
