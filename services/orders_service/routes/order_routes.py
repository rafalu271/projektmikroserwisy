from flask import Blueprint, jsonify, request, session
from db import db
from models import Order, OrderItem

order_blueprint = Blueprint('order_blueprint', __name__)

# Proces składania zamówienia
@order_blueprint.route('/order/checkout', methods=['POST'])
def checkout():
    cart_items = session.get('cart', [])
    if not cart_items:
        return jsonify({'message': 'Koszyk jest pusty'}), 400

    total_price = sum(item['quantity'] * 10.0 for item in cart_items)  # Przykład ceny produktu
    
    # Tworzenie nowego zamówienia
    order = Order(user_id=1, total_price=total_price, status='Oczekujące')  # Zakładając, że user_id to 1
    db.session.add(order)
    db.session.commit()

    # Dodawanie produktów do zamówienia
    for item in cart_items:
        order_item = OrderItem(order_id=order.id, product_id=item['product_id'], quantity=item['quantity'])
        db.session.add(order_item)
    
    db.session.commit()

    # Usuwanie koszyka po złożeniu zamówienia
    session.pop('cart', None)
    
    return jsonify({'message': 'Zamówienie zostało złożone', 'order_id': order.id}), 201

# Wyświetlanie szczegółów zamówienia
@order_blueprint.route('/order/<int:order_id>', methods=['GET'])
def get_order(order_id):
    order = Order.query.get_or_404(order_id)
    return jsonify({'id': order.id, 'user_id': order.user_id, 'total_price': order.total_price, 'status': order.status})

# Historia zamówień
@order_blueprint.route('/orders', methods=['GET'])
def get_orders():
    orders = Order.query.all()
    return jsonify([{
        'id': order.id,
        'user_id': order.user_id,
        'total_price': order.total_price,
        'status': order.status
    } for order in orders])
