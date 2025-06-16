from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_bcrypt import Bcrypt

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/product_images' # Relative to the app instance folder

db = SQLAlchemy(app)
migrate = Migrate(app, db)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login' # Route to redirect to if @login_required fails
login_manager.login_message_category = 'info' # Flash message category

from app import routes, models # utils will be imported in routes where needed

# Register context processors
from .context_processors import cart_contents_processor
app.context_processor(cart_contents_processor)

# Register Blueprints
from app.admin_routes import admin_bp
app.register_blueprint(admin_bp)
