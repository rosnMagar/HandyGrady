from . import bcrypt, db
from .models import User, Homework
from .forms import RegistrationForm, LoginForm, HomeworkForm
from .gemini import grade_answer_gemini

from flask import redirect, url_for, request, flash, render_template, abort, send_from_directory, current_app
from flask_login import current_user, login_user, login_required, logout_user
import plotly.express as px
import pandas as pd
import json

from uuid import uuid4
from uuid import UUID
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
                print(f"Processing {len(files)} files")  # Log number of files
                
                for idx, image in enumerate(files):
                    try:
                        if not image or image.filename == '':
                            print(f"Skipping empty file at index {idx}")
                            continue

                        filename = secure_filename(image.filename)
                        if not filename:
                            raise ValueError(f"Invalid filename at index {idx}")

                        unique_name = f"{uuid4().hex}_{filename}"
                        upload_dir = os.path.join(
                            current_app.root_path,
                            'static/uploads',
                            str(current_user.id),
                            str(homework.id)
                        )
                        
                        os.makedirs(upload_dir, exist_ok=True)
                        file_path = os.path.join(upload_dir, unique_name)
                        image.save(file_path)
                        print(f"Saved file {idx + 1}: {file_path}")  # Log success
                        
                        relative_path = '/'.join([
                            'uploads', 
                            str(current_user.id), 
                            str(homework.id), 
                            unique_name
                        ])
                        homework.add_image(relative_path)
                        print(f"Added path {idx + 1}: {relative_path}")  # Log path addition
            
                    except Exception as e:
                        print(f"Error processing file {idx + 1}: {str(e)}")
                        continue  # Skip problematic files

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
        
    @app.route('/homework/<string:hId>')
    def combined_charts(hId):

        homework = Homework.query.get(UUID(hId))
        
        scores = json.loads(homework.scores)
        subjects = [f"Section {i}" for i in range(1, len(scores) + 1)]

        overall_score = homework.final_score
        analysis = homework.analysis
        
        # Create pie chart
        pie_fig = px.pie(
            names=["Gained", "Lost"],
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
        
        return render_template('homework.html', pie_html=pie_html, bar_html=bar_html, analysis=analysis)
    
    
    @app.route('/grade_homework/<string:homework_id>', methods=['POST'])
    @login_required
    def grade_homework(homework_id):
        try:
            print("try11")
            # Fetch the homework object from the database
            homework = Homework.query.get(UUID(homework_id))
            
            if not homework:
                flash('Homework not found or you do not have permission to access it.', 'danger')
                return redirect(url_for('homework_upload'))

            # Fetch the relevant data for grading
            PROBLEM_IMAGES = homework.problem_images  # Replace with the actual attribute storing problem images
            ANSWER_IMAGES = homework.answer_images  # Replace with the actual attribute storing answer images
            GRADING_STANDARDS = homework.grading_standard  # Replace with the attribute storing grading standards

            # Call the `grade_answer_gemini` function
            result = grade_answer_gemini(
                PROBLEM_IMAGES, ANSWER_IMAGES, GRADING_STANDARDS, scoring_difficulty=5
            )
            print("grade_answer_gemini finish~~`a~~~~~~~~~~~~~~")
            print(result)
            
            print("Grading Results OVER")
            # Update the homework object with the returned values
            homework.scores = str(result['scores'])
            homework.analysis = str(result['analyses'])
            homework.final_score = result['final_score']
            homework.final_full_score = result['final_full_score']
            

            # Save modified image paths (if applicable)
            if 'modified_images' in result and result['modified_images']:
                homework.modified_images = str(result['modified_images'])  # Update homework with the paths

            # Commit the changes to the database
            db.session.commit()

            flash('Homework graded successfully!', 'success')
        except Exception as e:
            db.session.rollback()
            print("Error during grading:", str(e))  # Log the error for debugging
            flash(f'Error during grading: {str(e)}', 'danger')

        return redirect(url_for('homework_upload'))