from flask import session

def cart_contents_processor():
    cart = session.get('cart', {})
    item_count = 0
    cart_total = 0.0
    if isinstance(cart, dict): # Ensure cart is a dictionary
        item_count = sum(item.get('quantity', 0) for item in cart.values())
        cart_total = sum(item.get('quantity', 0) * item.get('price', 0) for item in cart.values())
    elif isinstance(cart, list): # Handle old list-based cart format if necessary (for transition)
        # This part is for compatibility if you previously stored cart as a list of items
        # And each item was a dict like {'product_id': pid, 'quantity': q, 'price': p, 'name': n}
        # If not, you can remove this elif block.
        item_count = sum(item.get('quantity', 0) for item in cart)
        cart_total = sum(item.get('quantity', 0) * item.get('price', 0) for item in cart)
        # Consider migrating old cart format to new dict format when user accesses cart

    # Make sure item_count is an integer and cart_total is a float
    if not isinstance(item_count, int):
        item_count = 0 # Or log an error, or try to convert
    if not isinstance(cart_total, float):
        try:
            cart_total = float(cart_total)
        except (ValueError, TypeError):
            cart_total = 0.0 # Or log an error

    return dict(cart_item_count=item_count, cart_total_amount=cart_total)
