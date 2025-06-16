from flask import render_template, url_for, flash, redirect, request, abort, session
from app import app, db, bcrypt
from app.forms import RegistrationForm, LoginForm, ProductForm
from app.models import User, Product, Order, OrderItem, Affiliate
from flask_login import login_user, current_user, logout_user, login_required
from app.utils import save_picture, delete_picture # Image saving utility, admin_required is in admin_routes
import os
from datetime import datetime

@app.route('/')
@app.route('/home')
def home():
    return render_template('home.html', title='Home')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        # New users are 'client' by default, admin can change roles later if needed
        db.session.add(user)
        db.session.commit()
        flash(f'Account created for {form.username.data}! You can now log in.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            flash('Login successful!', 'success')
            return redirect(next_page) if next_page else redirect(url_for('home'))
        else:
            flash('Login Unsuccessful. Please check email and password', 'danger')
    return render_template('login.html', title='Login', form=form)

@app.route('/logout')
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('home'))

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html', title='Dashboard')

# CRUD Routes for Products
@app.route('/product/new', methods=['GET', 'POST'])
@login_required
def add_product():
    if current_user.role != 'admin':
        abort(403)  # Forbidden access for non-admins
    form = ProductForm()
    if form.validate_on_submit():
        image_filename = None
        if form.image_file.data:
            image_filename = save_picture(form.image_file.data)

        product = Product(name=form.name.data,
                          description=form.description.data,
                          price=form.price.data,
                          stock=form.stock.data,
                          image_file=image_filename)
        db.session.add(product)
        db.session.commit()
        flash('Product added successfully!', 'success')
        return redirect(url_for('product_list')) # Or redirect to product_detail(product_id=product.id)
    return render_template('add_product.html', title='Add Product', form=form, legend='New Product')

@app.route('/product/<int:product_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_product(product_id):
    if current_user.role != 'admin':
        abort(403)
    product = Product.query.get_or_404(product_id)
    form = ProductForm()

    if form.validate_on_submit():
        if form.image_file.data:
            if product.image_file: # Delete old image if a new one is uploaded
                delete_picture(product.image_file)
            product.image_file = save_picture(form.image_file.data)

        product.name = form.name.data
        product.description = form.description.data
        product.price = form.price.data
        product.stock = form.stock.data
        db.session.commit()
        flash('Product updated successfully!', 'success')
        return redirect(url_for('product_detail', product_id=product.id))
    elif request.method == 'GET':
        form.name.data = product.name
        form.description.data = product.description
        form.price.data = product.price
        form.stock.data = product.stock
        # Image field is not pre-filled for editing, user has to upload new one if change needed
    return render_template('edit_product.html', title='Edit Product', form=form, legend=f'Edit {product.name}', product=product)

@app.route('/product/<int:product_id>/delete', methods=['POST']) # Should be POST for destructive action
@login_required
def delete_product(product_id):
    if current_user.role != 'admin':
        abort(403)
    product = Product.query.get_or_404(product_id)
    if product.image_file:
        delete_picture(product.image_file)
    db.session.delete(product)
    db.session.commit()
    flash('Product deleted successfully!', 'success')
    return redirect(url_for('product_list'))

@app.route('/product/<int:product_id>')
def product_detail(product_id):
    product = Product.query.get_or_404(product_id)
    image_url = None
    if product.image_file:
        image_url = url_for('static', filename=os.path.join('product_images', product.image_file))
    return render_template('product_detail.html', title=product.name, product=product, image_url=image_url)

@app.route('/products')
def product_list():
    page = request.args.get('page', 1, type=int)
    products = Product.query.order_by(Product.name.asc()).paginate(page=page, per_page=10) # Example pagination
    return render_template('product_list.html', title='Products', products=products)


# Cart Routes
@app.route('/cart/add/<int:product_id>', methods=['POST'])
def add_to_cart(product_id):
    product = Product.query.get_or_404(product_id)
    cart = session.get('cart', {}) # Use a dictionary for the cart for easier manipulation

    # Ensure product_id is string for session keys, as JSON serializes dict keys to strings
    str_product_id = str(product.id)

    quantity_to_add = int(request.form.get('quantity', 1)) # Get quantity from form, default to 1

    if product.stock <= 0 or (str_product_id in cart and cart[str_product_id]['quantity'] + quantity_to_add > product.stock):
        flash(f'Not enough stock for {product.name}. Only {product.stock} available.', 'warning')
        return redirect(request.referrer or url_for('product_detail', product_id=product_id))

    if str_product_id in cart:
        cart[str_product_id]['quantity'] += quantity_to_add
    else:
        cart[str_product_id] = {
            'name': product.name,
            'price': product.price,
            'quantity': quantity_to_add,
            'image': product.image_file # Storing image for cart display
        }

    session['cart'] = cart
    flash(f'{quantity_to_add} unit(s) of {product.name} added to your cart.', 'success')
    return redirect(request.referrer or url_for('cart_view'))


@app.route('/cart')
def cart_view():
    cart = session.get('cart', {})
    # The total calculation is now handled by the context processor (cart_total_amount)
    # but we can pass the cart itself for detailed display
    return render_template('cart.html', title='Your Shopping Cart', cart=cart)


@app.route('/cart/update/<int:product_id>', methods=['POST'])
def update_cart(product_id):
    cart = session.get('cart', {})
    str_product_id = str(product_id)
    product = Product.query.get_or_404(product_id) # For stock checking

    if str_product_id in cart:
        try:
            new_quantity = int(request.form.get('quantity'))
            if new_quantity < 0:
                flash('Quantity cannot be negative.', 'danger')
                return redirect(url_for('cart_view'))

            if new_quantity > product.stock:
                flash(f'Not enough stock for {product.name}. Only {product.stock} available.', 'warning')
                return redirect(url_for('cart_view'))

            if new_quantity == 0:
                del cart[str_product_id]
                flash(f'{product.name} removed from cart.', 'info')
            else:
                cart[str_product_id]['quantity'] = new_quantity
                flash(f'Quantity for {product.name} updated.', 'success')
            session['cart'] = cart
        except ValueError:
            flash('Invalid quantity specified.', 'danger')
    else:
        flash('Product not found in cart.', 'danger')
    return redirect(url_for('cart_view'))


@app.route('/cart/remove/<int:product_id>', methods=['POST']) # Should be POST
def remove_from_cart(product_id):
    cart = session.get('cart', {})
    str_product_id = str(product_id)

    if str_product_id in cart:
        product_name = cart[str_product_id].get('name', 'Product')
        del cart[str_product_id]
        session['cart'] = cart
        flash(f'{product_name} removed from your cart.', 'success')
    else:
        flash('Product not found in cart to remove.', 'warning')
    return redirect(url_for('cart_view'))


# Checkout and Order Processing Routes

@app.route('/checkout')
@login_required
def checkout():
    cart = session.get('cart', {})
    if not cart:
        flash('Your cart is empty. Add some products before checking out.', 'info')
        return redirect(url_for('cart_view'))

    # Total amount is already available via context processor 'cart_total_amount'
    # but it's good to pass it explicitly or recalculate for safety if needed here.
    current_cart_total = sum(item.get('quantity', 0) * item.get('price', 0) for item in cart.values())
    return render_template('checkout.html', title='Checkout', cart=cart, total_amount=current_cart_total)

@app.before_request
def track_affiliate_referral():
    ref_code = request.args.get('ref')
    if ref_code:
        affiliate = Affiliate.query.filter_by(affiliate_code=ref_code, is_active=True).first()
        if affiliate:
            if not current_user.is_authenticated or current_user.id != affiliate.user_id: # Don't let affiliates refer themselves
                 session['referred_by_affiliate_id'] = affiliate.id
                 # flash(f"Referred by {affiliate.user.username}", "info") # Optional: for debugging or transparency
            elif 'referred_by_affiliate_id' in session and current_user.is_authenticated and current_user.id == affiliate.user_id:
                 # If user logs in as the affiliate who referred them, clear the referral
                 session.pop('referred_by_affiliate_id', None)
        else:
            # Optional: if ref code is invalid, clear any existing one, or ignore
            session.pop('referred_by_affiliate_id', None)


@app.route('/process_payment', methods=['POST'])
@login_required
def process_payment():
    cart = session.get('cart', {})
    if not cart:
        flash('Your cart is empty.', 'danger')
        return redirect(url_for('cart_view'))

    # Simulate payment success
    payment_successful = True

    if payment_successful:
        try:
            total_order_amount = sum(item['quantity'] * item['price'] for item in cart.values())

            referred_affiliate_id = session.get('referred_by_affiliate_id')
            commission_amount = 0.0
            affiliate_instance = None

            if referred_affiliate_id:
                affiliate_instance = Affiliate.query.get(referred_affiliate_id)
                if affiliate_instance and affiliate_instance.is_active:
                     # Ensure the affiliate is not the customer themselves
                    if affiliate_instance.user_id != current_user.id:
                        commission_amount = total_order_amount * affiliate_instance.commission_rate
                    else: # Customer is the affiliate, invalidate referral for this order
                        referred_affiliate_id = None
                        affiliate_instance = None
                else: # Affiliate not found or inactive, invalidate
                    referred_affiliate_id = None
                    affiliate_instance = None

            order = Order(user_id=current_user.id,
                          total_amount=total_order_amount,
                          status='Paid',
                          affiliate_id=referred_affiliate_id,
                          commission_earned=commission_amount)
            db.session.add(order)
            db.session.flush()

            for product_id_str, item_data in cart.items():
                product_id = int(product_id_str)
                product = Product.query.get(product_id)
                if not product:
                    flash(f"Product {item_data['name']} not found. Order cancelled.", 'danger')
                    db.session.rollback()
                    return redirect(url_for('cart_view'))

                if product.stock < item_data['quantity']:
                    flash(f"Not enough stock for {product.name}. Order cancelled.", 'danger')
                    db.session.rollback()
                    return redirect(url_for('cart_view'))

                order_item = OrderItem(order_id=order.id,
                                       product_id=product.id,
                                       quantity=item_data['quantity'],
                                       price_at_purchase=item_data['price'])
                db.session.add(order_item)
                product.stock -= item_data['quantity']

            db.session.commit()

            session.pop('cart', None)
            session.pop('referred_by_affiliate_id', None) # Clear referral after use
            flash('Your order has been placed successfully!', 'success')
            return redirect(url_for('order_confirmation', order_id=order.id))
        except Exception as e:
            db.session.rollback()
            flash(f'An error occurred while processing your order: {str(e)}', 'danger')
            return redirect(url_for('checkout'))
    else:
        flash('Payment failed. Please try again.', 'danger')
        return redirect(url_for('checkout'))


@app.route('/order_confirmation/<int:order_id>')
@login_required
def order_confirmation(order_id):
    order = Order.query.get_or_404(order_id)
    if order.customer != current_user and current_user.role != 'admin':
        abort(403) # User can only view their own orders unless admin
    return render_template('order_confirmation.html', title='Order Confirmed', order=order)


@app.route('/order_history')
@login_required
def order_history():
    page = request.args.get('page', 1, type=int)
    orders = Order.query.filter_by(user_id=current_user.id)\
                        .order_by(Order.order_date.desc())\
                        .paginate(page=page, per_page=10)
    return render_template('order_history.html', title='Order History', orders=orders)


@app.route('/affiliate/dashboard')
@login_required
def affiliate_dashboard():
    affiliate_profile = current_user.affiliate_profile
    if not (affiliate_profile and affiliate_profile.is_active and current_user.role == 'affiliate'):
        flash('You do not have access to the affiliate dashboard.', 'warning')
        return redirect(url_for('home'))

    page = request.args.get('page', 1, type=int)
    referred_orders_query = Order.query.filter_by(affiliate_id=affiliate_profile.id)\
                                   .order_by(Order.order_date.desc())
    referred_orders = referred_orders_query.paginate(page=page, per_page=10)

    total_commission = db.session.query(db.func.sum(Order.commission_earned))\
                                .filter(Order.affiliate_id == affiliate_profile.id)\
                                .scalar() or 0.0

    referral_link = url_for('home', ref=affiliate_profile.affiliate_code, _external=True)

    return render_template('affiliate/dashboard.html',
                           title='Affiliate Dashboard',
                           affiliate=affiliate_profile,
                           referral_link=referral_link,
                           referred_orders=referred_orders,
                           total_commission=total_commission)


# Make sure UPLOAD_FOLDER path is correct in utils.py and __init__.py
# The UPLOAD_FOLDER in __init__.py is 'static/product_images'
# In utils.py, os.path.join(current_app.root_path, current_app.config['UPLOAD_FOLDER'], picture_fn)
# current_app.root_path is /app, so it becomes /app/app/static/product_images. This needs correction.
# It should be os.path.join(current_app.root_path, 'static/product_images', picture_fn) if UPLOAD_FOLDER is just 'product_images'
# Or, current_app.config['UPLOAD_FOLDER'] should be 'app/static/product_images' and utils should use it directly.
# The current setup in __init__ (app.config['UPLOAD_FOLDER'] = 'static/product_images') means utils.py will try to save to app/static/product_images
# The url_for for static files will also look into app/static. This seems correct.
# Let's ensure the directory app/static/product_images is created.
@app.before_first_request
def create_upload_folder():
    upload_dir = os.path.join(app.root_path, app.config['UPLOAD_FOLDER'])
    if not os.path.exists(upload_dir):
        os.makedirs(upload_dir)

# To assign a user as admin, you'd typically do this manually in the database or create a CLI command.
# For testing, you can modify a user's role after creation:
# from app.models import User
# user = User.query.filter_by(email='admin@example.com').first()
# if user:
#     user.role = 'admin'
#     db.session.commit()
