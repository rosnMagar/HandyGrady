from .extensions import db, login_manager
from flask_login import UserMixin
from flask import current_app, url_for
from werkzeug.utils import secure_filename
import uuid
from datetime import datetime
import json

class User(UserMixin, db.Model):
    id = db.Column(db.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)
    homeworks = db.relationship('Homework', backref='user', lazy=True)

from datetime import datetime  # Add this import

class Homework(db.Model):
    id = db.Column(db.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = db.Column(db.String(100), nullable=False)  # Add this line
    grading_standard = db.Column(db.String(100), nullable=False)
    image_paths = db.Column(db.Text, nullable=False, default='[]')
    grade = db.Column(db.String(20))
    analysis = db.Column(db.Text)
    user_id = db.Column(db.UUID(as_uuid=True), db.ForeignKey('user.id'), nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)  # Add this line

    def add_image(self, path):
        """Add an image path to the JSON list."""
        paths = json.loads(self.image_paths) if self.image_paths else []
        paths.append(path)
        self.image_paths = json.dumps(paths)

    def get_images(self):
        """Get a list of image paths."""
        return json.loads(self.image_paths) if self.image_paths else []

   
@login_manager.user_loader
def load_user(user_id):
    try:
        # Convert string to UUID
        return User.query.get(uuid.UUID(str(user_id)))
    except (ValueError, TypeError, AttributeError) as e:
        print(f"Invalid user ID: {user_id} - {str(e)}")
        return None