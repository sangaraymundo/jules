import os
import secrets
from werkzeug.utils import secure_filename
from flask import current_app, abort
from flask_login import current_user
from functools import wraps
import secrets
import uuid
# Import Affiliate model here to check for collisions, or pass db session/model as argument
# from app.models import Affiliate # This would create circular import if models import utils
# from app import db # This might also be problematic for circular imports.
# Best to pass Affiliate model or a checking function if high collision chance.
# For now, assume random generation is sufficient for uniqueness for this task.

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or getattr(current_user, 'role', 'client') != 'admin':
            abort(403)  # Forbidden
        return f(*args, **kwargs)
    return decorated_function

def generate_unique_affiliate_code(username_prefix='user'):
    """
    Generates a unique affiliate code.
    A simple approach using username and a short random hex.
    For higher uniqueness, a longer token or collision check against DB is needed.
    """
    # Clean username_prefix to be alphanumeric and short
    safe_prefix = "".join(filter(str.isalnum, username_prefix))[:5].lower()
    random_part = secrets.token_hex(4) # 8 characters
    # code = f"{safe_prefix}-{random_part}"
    # Alternative using UUID - generally longer but very unique
    code = uuid.uuid4().hex[:8].upper() # Example: 8 char uppercase hex

    # Collision check (conceptual - would require db access)
    # from app.models import Affiliate (or pass model)
    # while Affiliate.query.filter_by(affiliate_code=code).first():
    #     code = uuid.uuid4().hex[:8].upper() # Regenerate
    return code

def save_picture(form_picture):
    """
    Saves an uploaded picture to the filesystem.
    Returns the filename of the saved picture.
    """
    random_hex = secrets.token_hex(8)
    _, f_ext = os.path.splitext(form_picture.filename)
    picture_fn = random_hex + f_ext
    picture_path = os.path.join(current_app.root_path, current_app.config['UPLOAD_FOLDER'], picture_fn)

    # Create the directory if it doesn't exist
    output_dir = os.path.join(current_app.root_path, current_app.config['UPLOAD_FOLDER'])
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    form_picture.save(picture_path)
    return picture_fn

def delete_picture(filename):
    """
    Deletes a picture from the filesystem.
    """
    if filename and filename != 'default.jpg': # Assuming 'default.jpg' is a placeholder you might use
        picture_path = os.path.join(current_app.root_path, current_app.config['UPLOAD_FOLDER'], filename)
        if os.path.exists(picture_path):
            try:
                os.remove(picture_path)
                return True
            except Exception as e:
                print(f"Error deleting file {picture_path}: {e}")
                return False
        return False
    return False
