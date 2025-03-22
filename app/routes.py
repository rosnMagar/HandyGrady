from . import bcrypt, db
from .models import User
from .forms import RegistrationForm, LoginForm

from flask import redirect, url_for, request, flash, render_template 
from flask_login import current_user, login_user, login_required, logout_user

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
            hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
            user = User(username=form.username.data, email=form.email.data, password=hashed_password)
            db.session.add(user)
            db.session.commit()
            flash('Your account has been created! You can now log in', 'success')
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

    @app.route('/homework')
    @login_required
    def homework():
        print(f"User {current_user.username} accessed homework")
        return render_template("homework.html", title="Homework")

    @app.route('/chats')
    @login_required
    def chat():
        print(f"User {current_user.username} accessed chat")
        return render_template("chat.html", title="Chat")

    @app.route("/logout")
    def logout():
        logout_user()
        return redirect(url_for('home'))