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
    grading_standard = db.Column(db.Text, nullable=False)
    problem_images = db.Column(db.Text, nullable=False, default='[]')
    answer_images = db.Column(db.Text, nullable=False, default='[]')
    image_modifications = db.Column(db.Text, nullable=False, default='[]')
    analysis = db.Column(db.JSON)
    final_score = db.Column(db.Float)
    feedback = db.Column(db.Text)
    user_id = db.Column(db.UUID(as_uuid=True), db.ForeignKey('user.id'), nullable=False)

    def add_image(self, path):
        """Add an image path to the JSON list."""
        paths = json.loads(self.answer_images) if self.answer_images else []
        paths.append(path)
        self.answer_images = json.dumps(paths)

        paths2 = json.loads(self.problem_images) if self.problem_images else []
        paths2.append(paths2)
        self.problem_images = json.dumps(paths2)

    def get_images(self):
        """Get a list of image paths."""
        return json.loads(self.answer_images) if self.answer_images else []

   
@login_manager.user_loader
def load_user(user_id):
    try:
        # Convert string to UUID
        return User.query.get(uuid.UUID(str(user_id)))
    except (ValueError, TypeError, AttributeError) as e:
        print(f"Invalid user ID: {user_id} - {str(e)}")
        return None