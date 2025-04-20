from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone
from slugify import slugify  # Requires python-slugify package
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from flask_mail import Message

db = SQLAlchemy()


# Association tables (unchanged)
part_tags = db.Table('part_tags',
    db.Column('part_id', db.Integer, db.ForeignKey('Part.id'), primary_key=True),
    db.Column('tag_id', db.Integer, db.ForeignKey('Tag.id'), primary_key=True)
)


class User(UserMixin, db.Model):
    __tablename__ = 'User'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    role = db.Column(db.String(20), default='user')  # 'user', 'admin', 'superadmin'
    membership_number = db.Column(db.Integer, unique=True)
    membership_active = db.Column(db.Boolean, default=True)
    last_login = db.Column(db.DateTime)
    first_name = db.Column(db.String(50))
    last_name = db.Column(db.String(50))
    phone = db.Column(db.String(20))
    address_line1 = db.Column(db.String(100))
    address_line2 = db.Column(db.String(100))
    city = db.Column(db.String(50))
    postcode = db.Column(db.String(20))
    country = db.Column(db.String(50))
    account_active = db.Column(db.Boolean, default=False)

    # relationships
    orders = db.relationship('Order', back_populates='user', lazy='dynamic')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_active(self):
        return bool(self.account_active)

    @property
    def is_member(self):
        return self.membership_active and bool(self.membership_number)

    @property
    def is_admin(self):
        return self.role in ['admin', 'superadmin']

    @property
    def is_superadmin(self):
        return self.role == 'superadmin'


class Brand(db.Model):
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
    city = db.Column(db.String(50))
    details = db.Column(db.String(200))
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
    price_member = db.Column(db.Float)  # Price for members
    price_non_member = db.Column(db.Float)  # Price for non-members
    storage_details = db.Column(db.String(200))  # Storage details
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    brand_id = db.Column(db.Integer, db.ForeignKey('Brand.id'))
    location_id = db.Column(db.Integer, db.ForeignKey('Location.id'))
    part_type_id = db.Column(db.Integer, db.ForeignKey('PartType.id'))
    
    # Relationships
    brand = db.relationship('Brand', back_populates='parts')
    location = db.relationship('Location', back_populates='parts')
    images = db.relationship('Image', back_populates='part', cascade='all, delete-orphan')
    tags = db.relationship('Tag', secondary=part_tags, back_populates='parts')
    part_type = db.relationship('PartType')

    def get_price(self, user=None):
        """Return appropriate price based on user status"""
        if user and hasattr(user, 'is_member') and user.is_member:
            return self.price_member if self.price_member else 0
        return self.price_non_member if self.price_non_member else 0


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


class Order(db.Model):
    __tablename__ = 'Order'
    id = db.Column(db.Integer, primary_key=True)
    order_number = db.Column(db.String(20), unique=True)
    order_date = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    status = db.Column(db.String(20), default='pending')  # pending, processing, shipped, completed
    total_amount = db.Column(db.Float)
    member_discount = db.Column(db.Float, default=0.0)
    user_id = db.Column(db.Integer, db.ForeignKey('User.id'))

    # Relationships
    user = db.relationship('User', back_populates='orders')
    items = db.relationship('OrderItem', back_populates='order')


class OrderItem(db.Model):
    __tablename__ = 'OrderItem'
    id = db.Column(db.Integer, primary_key=True)
    quantity = db.Column(db.Integer, default=1)
    unit_price = db.Column(db.Float)
    order_id = db.Column(db.Integer, db.ForeignKey('Order.id'))
    part_id = db.Column(db.Integer, db.ForeignKey('Part.id'))

    # Relationships
    order = db.relationship('Order', back_populates='items')
    part = db.relationship('Part')


class Image(db.Model):
    __tablename__ = 'Image'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    filename = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(500))
    is_primary = db.Column(db.Boolean, default=False)
    sort_order = db.Column(db.Integer, default=0)
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
