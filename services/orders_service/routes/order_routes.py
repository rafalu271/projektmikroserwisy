from flask import Blueprint, jsonify, request, current_app
from db import db
from models import Order, OrderItem, Cart, CartItem
import jwt
from functools import wraps
import requests

order_blueprint = Blueprint('order_blueprint', __name__)

def get_product_service_url():
    """Funkcja pomocnicza do pobierania URL serwisu produktów"""
    product_service_url = current_app.config.get('PRODUCT_SERVICE_URL')
    if not product_service_url:
        raise ValueError("Nie można znaleźć URL serwisu produktów.")
    return product_service_url

# Funkcja pomocnicza do weryfikacji tokenu JWT
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization', '').split("Bearer ")[-1]  # Pobranie tokenu z nagłówka
        if not token:
            return jsonify({'message': 'Brak tokenu, dostęp zabroniony!'}), 401
        try:
            # Weryfikacja tokenu JWT
            decoded_token = jwt.decode(token, 'super_secret_key', algorithms=['HS256'])  # Upewnij się, że klucz tajny jest właściwy
            request.user_id = decoded_token['user_id']  # Dodanie user_id do requestu
        except jwt.ExpiredSignatureError:
            return jsonify({'message': 'Token wygasł!'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'message': 'Nieprawidłowy token!'}), 403
        return f(*args, **kwargs)
    return decorated


def verify_products_in_cart(cart_items):
    """Weryfikacja dostępności produktów w serwisie produktów"""
    product_service_url = get_product_service_url()

    for item in cart_items:
        product_id = item.product_id
        quantity = item.quantity

        try:
            response = requests.get(f"{product_service_url}/{product_id}")
            response.raise_for_status()
            product_data = response.json()

            if product_data['quantity'] < quantity:
                return False, f"Produkt ID {product_id} ma niewystarczającą ilość na stanie."
        except requests.exceptions.RequestException as e:
            current_app.logger.error(f"Błąd weryfikacji produktu ID {product_id}: {e}")
            return False, "Błąd weryfikacji produktów."
    return True, None


# Proces składania zamówienia
@order_blueprint.route('/order/checkout', methods=['POST'])
@token_required
def checkout():
    user_id = request.user_id  # Pobranie user_id z tokenu

    # Pobieranie koszyka użytkownika
    cart = Cart.query.filter_by(user_id=user_id).first()
    if not cart or not cart.items:
        return jsonify({'message': 'Koszyk jest pusty'}), 400

    # Weryfikacja dostępności produktów w serwisie produktów
    is_valid, error_message = verify_products_in_cart(cart.items)
    if not is_valid:
        return jsonify({'message': error_message}), 400

    # Obliczanie całkowitej ceny zamówienia
    total_price = 0
    for item in cart.items:
        product_id = item.product_id
        response = requests.get(f"{get_product_service_url()}/{product_id}")
        product_data = response.json()
        total_price += item.quantity * product_data['price']

    # Tworzenie nowego zamówienia
    order = Order(user_id=user_id, total_price=total_price, status='Oczekujące')
    db.session.add(order)
    db.session.commit()

    # Dodawanie produktów do zamówienia
    for item in cart.items:
        order_item = OrderItem(order_id=order.id, product_id=item.product_id, quantity=item.quantity)
        db.session.add(order_item)
    
    db.session.commit()

    # Usuwanie koszyka po złożeniu zamówienia
    db.session.delete(cart)
    db.session.commit()
    
    return jsonify({'message': 'Zamówienie zostało złożone', 'order_id': order.id}), 201


# Wyświetlanie szczegółów zamówienia
@order_blueprint.route('/order/<int:order_id>', methods=['GET'])
@token_required
def get_order(order_id):
    user_id = request.user_id  # Pobranie user_id z tokenu

    # Pobieranie zamówienia dla użytkownika
    order = Order.query.filter_by(id=order_id, user_id=user_id).first()
    if not order:
        return jsonify({'message': 'Zamówienie nie znalezione lub brak dostępu'}), 404

    order_items = [
        {'product_id': item.product_id, 'quantity': item.quantity}
        for item in order.items
    ]

    return jsonify({
        'id': order.id,
        'user_id': order.user_id,
        'total_price': order.total_price,
        'status': order.status,
        'items': order_items
    })

# Historia zamówień użytkownika
@order_blueprint.route('/orders', methods=['GET'])
@token_required
def get_orders():
    user_id = request.user_id  # Pobranie user_id z tokenu

    # Pobieranie zamówień użytkownika
    orders = Order.query.filter_by(user_id=user_id).all()

    return jsonify([{
        'id': order.id,
        'user_id': order.user_id,
        'total_price': order.total_price,
        'status': order.status,
        'items': [
            {'product_id': item.product_id, 'quantity': item.quantity}
            for item in order.items
        ]
    } for order in orders])
