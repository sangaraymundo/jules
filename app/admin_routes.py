from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db
from app.models import User, Product, Order, OrderItem, Affiliate
from app.utils import admin_required, generate_unique_affiliate_code
from sqlalchemy import func
from datetime import datetime, date, timedelta

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.route('/')
@admin_bp.route('/dashboard')
@login_required
@admin_required
def dashboard():
    # User, Product, Order counts
    user_count = User.query.count()
    product_count = Product.query.count()
    total_order_count = Order.query.count() # All orders

    # Sales statistics
    today = date.today()
    start_of_day = datetime(today.year, today.month, today.day)

    # Corrected: Use today for start_of_month to get current month
    start_of_month = datetime(today.year, today.month, 1)

    total_lifetime_sales = db.session.query(func.sum(Order.total_amount))\
                                     .filter(Order.status == 'Paid')\
                                     .scalar() or 0.0

    sales_today = db.session.query(func.sum(Order.total_amount))\
                            .filter(Order.status == 'Paid', Order.order_date >= start_of_day)\
                            .scalar() or 0.0

    sales_this_month = db.session.query(func.sum(Order.total_amount))\
                               .filter(Order.status == 'Paid', Order.order_date >= start_of_month)\
                               .scalar() or 0.0

    total_commission_paid = db.session.query(func.sum(Order.commission_earned))\
                                      .filter(Order.affiliate_id != None, Order.status == 'Paid')\
                                      .scalar() or 0.0 # Assuming commission is "paid" when order is "paid"

    orders_today_count = db.session.query(func.count(Order.id))\
                                   .filter(Order.order_date >= start_of_day)\
                                   .scalar() or 0

    orders_this_month_count = db.session.query(func.count(Order.id))\
                                      .filter(Order.order_date >= start_of_month)\
                                      .scalar() or 0

    # Paid orders count for this month
    paid_orders_this_month_count = db.session.query(func.count(Order.id))\
                                          .filter(Order.status == 'Paid', Order.order_date >= start_of_month)\
                                          .scalar() or 0

    paid_orders_today_count = db.session.query(func.count(Order.id))\
                                        .filter(Order.status == 'Paid', Order.order_date >= start_of_day)\
                                        .scalar() or 0


    return render_template('admin/dashboard.html', title='Admin Dashboard',
                           user_count=user_count, product_count=product_count,
                           total_order_count=total_order_count,
                           total_lifetime_sales=total_lifetime_sales,
                           sales_today=sales_today,
                           sales_this_month=sales_this_month,
                           total_commission_paid=total_commission_paid,
                           orders_today_count=orders_today_count,
                           paid_orders_today_count=paid_orders_today_count,
                           orders_this_month_count=orders_this_month_count,
                           paid_orders_this_month_count=paid_orders_this_month_count
                           )

@admin_bp.route('/users')
@login_required
@admin_required
def manage_users():
    page = request.args.get('page', 1, type=int)
    users = User.query.order_by(User.id.asc()).paginate(page=page, per_page=15)
    return render_template('admin/manage_users.html', title='Manage Users', users=users)

@admin_bp.route('/user/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_user(user_id):
    user_to_edit = User.query.get_or_404(user_id)
    affiliate_profile = user_to_edit.affiliate_profile

    if request.method == 'POST':
        original_role = user_to_edit.role
        new_role = request.form.get('role')
        new_is_active_str = request.form.get('is_active')

        # Role update logic
        if new_role and new_role in ['client', 'admin', 'affiliate']:
            if user_to_edit.id == current_user.id and original_role == 'admin' and new_role != 'admin':
                if User.query.filter_by(role='admin').count() <= 1:
                    flash('Cannot remove the only admin role.', 'danger')
                    return redirect(url_for('admin.edit_user', user_id=user_id))
            user_to_edit.role = new_role

        # Activation status
        if new_is_active_str is not None:
            new_is_active = new_is_active_str.lower() == 'true'
            if user_to_edit.id == current_user.id and original_role == 'admin' and not new_is_active:
                if User.query.filter_by(role='admin', is_active=True).count() <= 1:
                    flash('Cannot deactivate the only active admin.', 'danger')
                    return redirect(url_for('admin.edit_user', user_id=user_id))
            user_to_edit.is_active = new_is_active

        # Affiliate specific logic
        if new_role == 'affiliate':
            if not affiliate_profile:
                # Create new affiliate profile
                new_affiliate_code = generate_unique_affiliate_code(user_to_edit.username)
                while Affiliate.query.filter_by(affiliate_code=new_affiliate_code).first(): # Ensure uniqueness
                    new_affiliate_code = generate_unique_affiliate_code(user_to_edit.username + "X")

                affiliate_profile = Affiliate(user_id=user_to_edit.id,
                                              affiliate_code=new_affiliate_code)
                db.session.add(affiliate_profile)
                flash(f'Affiliate profile created for {user_to_edit.username} with code {new_affiliate_code}.', 'info')

            # Update affiliate details from form
            affiliate_profile.is_active = request.form.get('affiliate_is_active') == 'true'
            try:
                commission_rate_str = request.form.get('commission_rate')
                if commission_rate_str: # Check if field was submitted
                    commission_rate = float(commission_rate_str)
                    if 0.0 <= commission_rate <= 1.0: # Example validation: 0% to 100%
                        affiliate_profile.commission_rate = commission_rate
                    else:
                        flash('Commission rate must be between 0.0 and 1.0.', 'warning')
            except ValueError:
                flash('Invalid commission rate format.', 'warning')

        elif original_role == 'affiliate' and new_role != 'affiliate' and affiliate_profile:
            # If role changed from affiliate to something else, consider deactivating or deleting affiliate profile
            # For now, let's just deactivate the affiliate profile
            affiliate_profile.is_active = False
            flash(f'Affiliate profile for {user_to_edit.username} has been deactivated due to role change.', 'info')

        db.session.commit()
        flash(f'User {user_to_edit.username} updated successfully.', 'success')
        return redirect(url_for('admin.manage_users'))

    available_roles = ['client', 'admin', 'affiliate']
    return render_template('admin/edit_user.html', title=f'Edit User {user_to_edit.username}',
                           user_to_edit=user_to_edit, affiliate_profile=affiliate_profile,
                           available_roles=available_roles)

@admin_bp.route('/products')
@login_required
@admin_required
def manage_products():
    # For now, just redirect to the main product list which has admin controls
    # Or list products here with direct admin actions
    return redirect(url_for('product_list'))

@admin_bp.route('/affiliates')
@login_required
@admin_required
def manage_affiliates():
    page = request.args.get('page', 1, type=int)
    # Querying affiliates and joining with User to get username/email
    # Also calculating total commission earned per affiliate
    affiliates_query = db.session.query(
        Affiliate,
        db.func.sum(Order.commission_earned).label('total_commission_earned')
    ).outerjoin(Order, Affiliate.id == Order.affiliate_id)\
     .group_by(Affiliate.id)\
     .order_by(Affiliate.created_at.desc())

    affiliates = affiliates_query.paginate(page=page, per_page=15)

    return render_template('admin/manage_affiliates.html', title='Manage Affiliates', affiliates=affiliates)


@admin_bp.route('/orders')
@login_required
@admin_required
def manage_orders():
    page = request.args.get('page', 1, type=int)
    status_filter = request.args.get('status', None)

    query = Order.query.order_by(Order.order_date.desc())
    if status_filter and status_filter != 'all':
        query = query.filter(Order.status == status_filter)

    orders = query.paginate(page=page, per_page=15)

    available_statuses = db.session.query(Order.status).distinct().all()
    available_statuses = [s[0] for s in available_statuses if s[0]] # Get unique, non-null statuses

    return render_template('admin/manage_orders.html', title='Manage Orders', orders=orders,
                           available_statuses=available_statuses, current_status=status_filter)

@admin_bp.route('/order/<int:order_id>')
@login_required
@admin_required
def order_detail(order_id):
    order = Order.query.get_or_404(order_id)
    # No need to check if admin owns it, admin can see all orders
    return render_template('admin/order_detail.html', title=f'Order #{order.id} Details', order=order)
