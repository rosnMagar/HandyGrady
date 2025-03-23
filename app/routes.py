from . import bcrypt, db
from .models import User, Homework
from .forms import RegistrationForm, LoginForm, HomeworkForm

from flask import redirect, url_for, request, flash, render_template, abort, send_from_directory, current_app
from flask_login import current_user, login_user, login_required, logout_user
import plotly.express as px
import pandas as pd
import json

from uuid import uuid4
import os
import json
import shutil
from datetime import datetime
from werkzeug.utils import secure_filename


def init_routes(app):
    @app.route("/")
    @app.route("/home")
    def home():
        return render_template('index.html')

    @app.route("/register", methods=['GET', 'POST'])
    def register():
        if current_user.is_authenticated:
            return redirect(url_for('home'))
        
        form = RegistrationForm()
        if form.validate_on_submit():
            # Explicitly create UUID
            uid = uuid4()
            hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
            
            user = User(
                id=uid,
                username=form.username.data,
                email=form.email.data,
                password=hashed_password
            )
            
            db.session.add(user)
            db.session.commit()
            flash('Account created! Please login', 'success')
            return redirect(url_for('login'))
        
        return render_template('register.html', title='Register', form=form)

    @app.route("/login", methods=['GET', 'POST'])
    def login():
        # Redirect authenticated users immediately
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))

        form = LoginForm()
        
        if form.validate_on_submit():
            user = User.query.filter_by(email=form.email.data).first()
            
            # Debugging checks
            print(f"User exists: {bool(user)}")
            if user:
                print(f"Password match: {bcrypt.check_password_hash(user.password, form.password.data)}")
            
            if user and bcrypt.check_password_hash(user.password, form.password.data):
                login_user(user)
                next_page = request.args.get('next')
                
                # Force URL validation for 'next' parameter
                if not next_page or url_parse(next_page).netloc != '':
                    next_page = url_for('dashboard')
                
                print(f"Redirecting to: {next_page}")
                return redirect(next_page)
            else:
                flash('Login Unsuccessful. Please check email and password', 'danger')
        
        # Print form errors if validation fails
        if form.errors:
            print(f"Form errors: {form.errors}")
        
        return render_template('login.html', title='Login', form=form)

    @app.route('/dashboard')
    @login_required  # Ensure this decorator is present
    def dashboard():
        print(f"User {current_user.email} accessed dashboard")  # Debug print
        return render_template('dashboard.html', title='Dashboard')

    @app.route('/chats')
    @login_required
    def chat():
        print(f"User {current_user.username} accessed chat")
        return render_template("chat.html", title="Chat")

    @app.route("/logout")
    def logout():
        logout_user()
        return redirect(url_for('home'))
    

    # homework
    # Add after your existing routes
    @app.route('/homework_upload', methods=['GET', 'POST'])
    @login_required
    def homework_upload():
        
        form = HomeworkForm()
        
        if request.method == 'POST':
            print("Form Data:", form.data)  # Debug submitted data
            print("Form Errors:", form.errors)  # Show validation errors
        try:
            homework = Homework(
                title=form.title.data,  # Ensure this is populated
                grading_standard=form.grading_standard.data,  # Ensure this is populated
                user_id=current_user.id
            )
            db.session.add(homework)
            db.session.flush()  # Generate ID without committing

            # Process uploaded images
            if form.images.data:
                files = form.images.data if isinstance(form.images.data, list) else [form.images.data]
                for image in files:
                    if image.filename:  # Check if a file was uploaded
                        # Save the image and store its path
                        filename = secure_filename(image.filename)
                        unique_name = f"{uuid4().hex}_{filename}"
                        upload_dir = os.path.join(
                            current_app.root_path,
                            'static/uploads',
                            str(current_user.id),
                            str(homework.id)
                        )
                        os.makedirs(upload_dir, exist_ok=True)  # Create directory if it doesn't exist
                        file_path = os.path.join(upload_dir, unique_name)
                        image.save(file_path)

                        relative_path = '/'.join(['uploads', str(current_user.id), str(homework.id), unique_name])
                        homework.add_image(relative_path)

            db.session.commit()
            flash('Homework created successfully!', 'success')
            return redirect(url_for('homework_upload'))

        except Exception as e:
            db.session.rollback()
            print("Database error:", str(e))  # Detailed error
            flash(f'Database error: {str(e)}', 'danger')

        homeworks = Homework.query.filter_by(user_id=current_user.id).all()
        return render_template('homework_upload.html', form=form, homeworks=homeworks)

    @app.route('/uploads/<path:filename>')
    def uploaded_file(filename):
        # Convert forward slashes to the system's path separator
        file_path = os.path.join(current_app.root_path, 'static', *filename.split('/'))
        return send_from_directory(os.path.dirname(file_path), os.path.basename(file_path))
        
    @app.route('/homework/hId')
    def combined_charts(hId):

        homework = User.query.filter_by(id=hId).first()
        print(homework)

        # Sample data
        subjects = ["Math", "Science", "History", "English"]
        scores = [90, 85, 78, 88]

        overall_score = 95
        
        # Create pie chart
        pie_fig = px.pie(
            names=["correct","incorrect"],
            values=[overall_score, 100 - overall_score],
            title='Score Distribution',
            hole=0.4,
            color_discrete_sequence=px.colors.sequential.RdBu
        )
        
        # Create bar chart
        bar_fig = px.bar(
            x=subjects,
            y=scores,
            title='Each Scores',
            labels={'x': 'Subject', 'y': 'Score'},
            color=subjects,
            text_auto=True
        )
        
        # Convert figures to HTML
        pie_html = pie_fig.to_html(full_html=False)
        bar_html = bar_fig.to_html(full_html=False)
        
        return render_template('homework.html', pie_html=pie_html, bar_html=bar_html)
