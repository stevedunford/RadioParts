from app.routes import db


class Image(db.Model):
    __tablename__ = 'Image'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    filename = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(255))
    tags = db.relationship('Tag', secondary='ImageTag', backref='images')


class Tag(db.Model):
    __tablename__ = 'Tag'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), nullable=False)


class ImageTag(db.Model):
    __tablename__ = 'ImageTag'
    iid = db.Column(db.Integer, db.ForeignKey('Image.id'), primary_key=True)
    tid = db.Column(db.Integer, db.ForeignKey('Tag.id'), primary_key=True)
