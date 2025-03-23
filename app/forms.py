from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, TextAreaField, SelectField
from wtforms.validators import DataRequired, Length, Email, EqualTo
from flask_wtf.file import FileField, FileAllowed
from wtforms import validators

class RegistrationForm(FlaskForm):
    username = StringField('Username',
        validators=[DataRequired(), Length(min=2, max=20)])
    email = StringField('Email',
        validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password',
        validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Sign Up')

class LoginForm(FlaskForm):
    email = StringField('Email',
        validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

class HomeworkForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired()])  # Must have DataRequired
    grading_standard = SelectField(
        'Grading Standard',
        choices=[('AP', 'AP Scoring'), ('IB', 'IB Rubric'), ('Custom', 'Custom Standard')],
        validators=[DataRequired()]  # Add this validator
    )
    images = FileField('Upload Images', validators=[
        FileAllowed(['jpg', 'jpeg', 'png', 'gif'], 'Images only!')
    ], render_kw={"multiple": True})
    analysis = TextAreaField('Analysis')
    submit = SubmitField('Submit Homework')
