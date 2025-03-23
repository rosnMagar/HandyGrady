
from .models import User, Homework
from .forms import RegistrationForm, LoginForm, HomeworkForm

from flask import redirect, url_for, request, flash, render_template, abort, send_from_directory, current_app
from flask_login import current_user, login_user, login_required, logout_user
import plotly.express as px
import pandas as pd
import json

import json
from werkzeug.utils import secure_filename

import google.generativeai as genai
from PIL import Image, ImageDraw, ImageFont  # Import ImageFont
import io
import json
from dotenv import load_dotenv
import os

try:
    print('a')
    if isinstance(image_data, str):  # assume it's a path
        print('b')
        print( Image.open(image_data))
    elif isinstance(image_data, bytes):  # it's already the image data
        
        print('c')
        print(Image.open(io.BytesIO(image_data)))  # use io.BytesIO to convert bytes to file-like object
    else:
        print('d')
        raise TypeError("Image data must be a file path (string) or image data (bytes).")
except FileNotFoundError:
    raise FileNotFoundError(f"Image file not found: {image_data}")
except Exception as e:
    raise Exception(f"Error loading image: {e}")