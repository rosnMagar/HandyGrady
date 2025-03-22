from .extensions import db, login_manager
from flask_login import UserMixin
import uuid
import json

class User(UserMixin, db.Model):
    id = db.Column(db.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)
    homeworks = db.relationship('Homework', back_populates='user', cascade='all, delete-orphan')

class Homework(db.Model):
    id = db.Column(db.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = db.Column(db.String(100), nullable=False)
    subject = db.Column(db.String(50), nullable=False)
    due_date = db.Column((db.Date), nullable=False)
    image_paths = db.Column((db.Text), nullable=False, default='[]')  # JSON list of paths
    analysis = db.Column((db.Text), nullable=False, default='[]')  # JSON list of paths
    user_id = db.Column(db.UUID(as_uuid=True), db.ForeignKey('user.id'), nullable=False)
    
    user = db.relationship('User', back_populates='homeworks')

    def add_image(self, path):
        """Add image path to homework"""
        paths = json.loads(self.image_paths)
        paths.append(path)
        self.image_paths = json.dumps(paths)

    def get_images(self):
        """Get list of image paths"""
        return json.loads(self.image_paths)

    def __repr__(self):
        return f'<Homework {self.title} ({self.subject})>'

@login_manager.user_loader
def load_user(user_id):
    try:
        # Convert string UUID from session to UUID object
        return User.query.get(uuid.UUID(user_id))
    except (ValueError, TypeError) as e:
        print(f"Invalid user ID format: {e}")
        return None