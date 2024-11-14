from flask import Blueprint, jsonify, request, session
from db import db
from models import Cart, CartItem

cart_blueprint = Blueprint('cart_blueprint', __name__)

# Dodawanie produktów do koszyka
@cart_blueprint.route('/cart/add', methods=['POST'])
def add_to_cart():
    data = request.get_json()
    product_id = data.get('product_id')
    quantity = data.get('quantity', 1)
    
    if 'cart' not in session:
        session['cart'] = []

    session['cart'].append({'product_id': product_id, 'quantity': quantity})
    return jsonify({'message': 'Produkt dodany do koszyka'}), 200

# Wyświetlanie zawartości koszyka
@cart_blueprint.route('/cart', methods=['GET'])
def get_cart():
    cart_items = session.get('cart', [])
    return jsonify(cart_items), 200
