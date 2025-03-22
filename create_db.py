from app import create_app
from app.extensions import db

def initialize_database():
    # Create the Flask application
    app = create_app()
    
    with app.app_context():
        # Create all database tables
        db.create_all()
        print("Database tables created successfully!")
        
        # Optional: Add initial data
        # from app.models import User
        # if not User.query.first():
        #     admin = User(username='admin', email='admin@example.com', password='adminpass')
        #     db.session.add(admin)
        #     db.session.commit()
        #     print("Initial admin user created")

if __name__ == '__main__':
    initialize_database()
