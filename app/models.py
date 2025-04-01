from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone
from slugify import slugify  # Requires python-slugify package


db = SQLAlchemy()


# Association tables (unchanged)
part_tags = db.Table('part_tags',
    db.Column('part_id', db.Integer, db.ForeignKey('Part.id'), primary_key=True),
    db.Column('tag_id', db.Integer, db.ForeignKey('Tag.id'), primary_key=True),
    db.Column('created_at', db.DateTime, default=datetime.now(timezone.utc))
)


class Brand(db.Model):
    """Radio manufacturers"""
    __tablename__ = 'Brand'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)  # "Philips"
    alias = db.Column(db.String(50), unique=True)  # "philips"
    description = db.Column(db.Text(500))
    logo_filename = db.Column(db.String(100))
    website = db.Column(db.String(200))

    # Automatically generate alias/slug on creation
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.alias:
            self.alias = slugify(self.name)

    # Relationships
    parts = db.relationship('Part', back_populates='brand')


class Location(db.Model):
    """Physical storage locations (libraries)"""
    __tablename__ = 'Location'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True)
    librarian_email = db.Column(db.String(120))
    address = db.Column(db.String(120))

    # Relationships
    parts = db.relationship('Part', back_populates='location')
    images = db.relationship('Image', back_populates='location')


class Part(db.Model):
    """Vintage radio components"""
    __tablename__ = 'Part'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)  # "Dial", "Valve"
    description = db.Column(db.String(1024))
    part_number = db.Column(db.String(30))
    quantity = db.Column(db.Integer, default=1)
    box = db.Column(db.String(20))            # "Box 3A"
    position = db.Column(db.String(50))       # "Bottom shelf"
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    brand_id = db.Column(db.Integer, db.ForeignKey('Brand.id'))
    location_id = db.Column(db.Integer, db.ForeignKey('Location.id'))
    part_type_id = db.Column(db.Integer, db.ForeignKey('PartType.id'))
    
    # Relationships
    brand = db.relationship('Brand', back_populates='parts')
    location = db.relationship('Location', back_populates='parts')
    images = db.relationship('Image', back_populates='part')
    tags = db.relationship('Tag', secondary=part_tags, back_populates='parts')
    part_type = db.relationship('PartType')


class PartType(db.Model):
    """Broad categories for radio parts (Tubes, Capacitors, etc.)"""
    __tablename__ = 'PartType'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)  # "Tube"
    description = db.Column(db.String(1024))  # "Vacuum tubes/valves for amplification"

    # Automatically generate slug for URLs
    slug = db.Column(db.String(50), unique=True)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.slug:
            self.slug = slugify(self.name)
    

class PartRequest(db.Model):
    __tablename__ = 'PartRequest'
    id = db.Column(db.Integer, primary_key=True)
    part_id = db.Column(db.Integer, db.ForeignKey('Part.id'))
    requester_email = db.Column(db.String(120))
    notes = db.Column(db.String(1024))                # "Need for 1947 Philips restoration"
    status = db.Column(db.String(20))         # "Pending", "Fulfilled"


class Image(db.Model):
    __tablename__ = 'Image'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    filename = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(500))
    created_at = db.Column(db.DateTime,
                           default=lambda: datetime.now(timezone.utc))
    location_id = db.Column(db.Integer, db.ForeignKey('Location.id'))
    part_id = db.Column(db.Integer, db.ForeignKey('Part.id'))

    # Relationship to tags
    location = db.relationship('Location', back_populates='images')
    part = db.relationship('Part', back_populates='images')
    
    def to_dict(self):
        return {
            'id': self.id,
            'filename': self.filename,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'description': self.description,
            'tags': [tag.to_dict() for tag in self.tags]
        }
    
    def verify_association(self):
        """Ensure consistent relationship state"""
        if self.part_id and self.part not in self.part.images:
            self.part.images.append(self)
        return self


class Tag(db.Model):
    __tablename__ = 'Tag'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.String(255))
    slug = db.Column(db.String(100), nullable=False, unique=True, index=True)
    
    # Relationships
    parts = db.relationship('Part', secondary=part_tags, back_populates='tags')

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.slug:
            self.slug = slugify(self.name)
