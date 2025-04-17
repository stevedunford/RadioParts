# blueprints/orders.py
from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from flask_login import login_required, current_user
from datetime import datetime
import random
import string
from ..models import db, Order, OrderItem, Part


bp = Blueprint('orders', __name__, url_prefix='/orders')


def generate_order_number():
    """Generate vintage-style order number (VR-YYYYMMDD-XXXXX)"""
    date_part = datetime.now().strftime('%Y%m%d')
    random_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
    return f"VR-{date_part}-{random_part}"


@bp.route('/cart')
@login_required
def cart():
    """Display the shopping cart with member/non-member pricing"""
    cart_items = []
    total = 0.0
    member_discount = 0.0

    for part_id, quantity in session.get('cart', {}).items():
        part = Part.query.get(part_id)
        if part:
            unit_price = part.price_member if current_user.is_member else part.price_non_member
            subtotal = unit_price * quantity
            cart_items.append({
                'part': part,
                'quantity': quantity,
                'unit_price': unit_price,
                'subtotal': subtotal
            })
            total += subtotal

    # Calculate member discount if applicable
    if current_user.is_member:
        member_discount = sum(
            (item['part'].price_non_member - item['part'].price_member) * item['quantity']
            for item in cart_items
        )

    return render_template('orders/cart.html', 
                           cart_items=cart_items,
                           total=total,
                           member_discount=member_discount,
                           is_member=current_user.is_member)


@bp.route('/cart/add/<int:part_id>', methods=['POST'])
@login_required
def add_to_cart(part_id):
    """Add an item to the cart"""
    part = Part.query.get_or_404(part_id)
    try:
        quantity = int(request.form.get('quantity', 1))
        if quantity <= 0:
            raise ValueError
    except (TypeError, ValueError):
        flash('Invalid quantity', 'error')
        return redirect(request.referrer or url_for('parts.gallery'))

    # Stock validation
    if quantity > part.quantity:
        flash(f'Only {part.quantity} available in stock', 'error')
        return redirect(request.referrer)

    # Initialize cart if not exists
    if 'cart' not in session:
        session['cart'] = {}

    # Add or update item in cart
    cart = session['cart']
    cart[str(part_id)] = cart.get(str(part_id), 0) + quantity
    session['cart'] = cart

    flash(f'Added {quantity} x {part.name} to your cart', 'success')
    return redirect(request.referrer or url_for('parts.gallery'))


@bp.route('/cart/update/<int:part_id>', methods=['POST'])
@login_required
def update_cart(part_id):
    """Update quantity of a cart item"""
    part = Part.query.get_or_404(part_id)
    quantity = int(request.form.get('quantity', 1))

    if quantity <= 0:
        return remove_from_cart(part_id)

    cart = session.get('cart', {})
    cart[str(part_id)] = quantity
    session['cart'] = cart

    flash(f'Updated {part.name} quantity to {quantity}', 'success')
    return redirect(url_for('orders.cart'))


@bp.route('/cart/remove/<int:part_id>')
@login_required
def remove_from_cart(part_id):
    """Remove an item from the cart"""
    part = Part.query.get_or_404(part_id)
    cart = session.get('cart', {})

    if str(part_id) in cart:
        del cart[str(part_id)]
        session['cart'] = cart
        flash(f'Removed {part.name} from your cart', 'info')

    return redirect(url_for('orders.cart'))


@bp.route('/checkout', methods=['GET', 'POST'])
@login_required
def checkout():
    """Process order checkout"""
    if 'cart' not in session or not session['cart']:
        flash('Your cart is empty', 'warning')
        return redirect(url_for('parts.gallery'))

    if request.method == 'POST':
        try:
            # Calculate total with member pricing
            total = 0.0
            order_items = []

            for part_id, quantity in session['cart'].items():
                part = Part.query.get(part_id)
                if part:
                    price = part.price_member if current_user.is_member else part.price_non_member
                    total += price * quantity
                    order_items.append({
                        'part': part,
                        'quantity': quantity,
                        'price': price
                    })

            # Create order
            order = Order(
                order_number=generate_order_number(),
                user_id=current_user.id,
                total_amount=total,
                member_discount=0.0,  # Will calculate below
                status='pending'
            )

            # Calculate member discount if applicable
            if current_user.is_member:
                non_member_total = sum(
                    item['part'].price_non_member * item['quantity']
                    for item in order_items
                )
                order.member_discount = non_member_total - total

            db.session.add(order)
            db.session.flush()  # Get order ID for items

            # Add order items
            for item in order_items:
                order_item = OrderItem(
                    order_id=order.id,
                    part_id=item['part'].id,
                    quantity=item['quantity'],
                    unit_price=item['price']
                )
                db.session.add(order_item)

            db.session.commit()

            # Clear cart
            session.pop('cart', None)

            flash(f'Order #{order.order_number} created successfully!', 'success')
            return redirect(url_for('orders.order_confirmation', order_id=order.id))

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f'Checkout error: {str(e)}')
            flash('An error occurred during checkout. Please try again.', 'error')
            return redirect(url_for('orders.cart'))

    # GET request - show checkout page
    return render_template('orders/checkout.html')


@bp.route('/order/<int:order_id>')
@login_required
def order_confirmation(order_id):
    """Show order confirmation"""
    order = Order.query.get_or_404(order_id)

    # Verify order belongs to current user
    if order.user_id != current_user.id and not current_user.is_admin:
        abort(403)

    return render_template('orders/confirmation.html', order=order)


@bp.route('/history')
@login_required
def history():
    """Show order history for the user"""
    orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.order_date.desc()).all()
    return render_template('orders/history.html', orders=orders)