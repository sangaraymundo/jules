from datetime import datetime
from app import db, bcrypt, login_manager
from flask_login import UserMixin

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    role = db.Column(db.String(20), nullable=False, default='client') # 'client', 'admin', 'affiliate'
    is_active = db.Column(db.Boolean, default=True)
    orders = db.relationship('Order', backref='customer', lazy=True)
    affiliate_profile = db.relationship('Affiliate', backref='user', uselist=False, cascade="all, delete-orphan")

    def set_password(self, password):
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    price = db.Column(db.Float, nullable=False)
    stock = db.Column(db.Integer, nullable=False, default=0)
    image_file = db.Column(db.String(100)) # Optional
    order_items = db.relationship('OrderItem', backref='product', lazy=True)

    def __repr__(self):
        return f'<Product {self.name}>'

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    affiliate_id = db.Column(db.Integer, db.ForeignKey('affiliate.id'), nullable=True)
    order_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    total_amount = db.Column(db.Float, nullable=False, default=0.0)
    commission_earned = db.Column(db.Float, nullable=True, default=0.0)
    status = db.Column(db.String(20), nullable=False, default='pending') # 'pending', 'paid', 'shipped', 'cancelled'
    items = db.relationship('OrderItem', backref='order', lazy=True, cascade="all, delete-orphan")
    referrer = db.relationship('Affiliate', backref='referred_orders', lazy=True)

    def __repr__(self):
        return f'<Order {self.id}>'

class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    price_at_purchase = db.Column(db.Float, nullable=False) # Store price at time of purchase

    def __repr__(self):
        return f'<OrderItem Order:{self.order_id} Product:{self.product_id} Qty:{self.quantity}>'

class Affiliate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), unique=True, nullable=False)
    affiliate_code = db.Column(db.String(50), unique=True, nullable=False)
    commission_rate = db.Column(db.Float, nullable=False, default=0.1) # 10% commission
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    # user = db.relationship('User', backref=db.backref('affiliate', uselist=False)) # This is covered by User.affiliate_profile

    def __repr__(self):
        return f'<Affiliate Code:{self.affiliate_code} User:{self.user_id} Rate:{self.commission_rate}>'
