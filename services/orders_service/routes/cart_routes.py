from flask import Blueprint, jsonify, request, current_app
from db import db
from models import Cart, CartItem
import jwt
from functools import wraps
import requests
import consul

cart_blueprint = Blueprint('cart_blueprint', __name__)

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


# Dodawanie produktów do koszyka
@cart_blueprint.route('/cart/add', methods=['POST'])
@token_required
def add_to_cart():
    data = request.get_json()
    product_id = data.get('product_id')
    quantity = data.get('quantity', 1)

    if not product_id:
        return jsonify({'message': 'Brak ID produktu'}), 400

    # Pobieranie URL serwisu produktów i weryfikacja produktu
    try:
        product_service_url = get_product_service_url()  # Funkcja pomocnicza do pobierania URL
        response = requests.get(f"{product_service_url}/{product_id}", timeout=5)  # Dodano timeout
        response.raise_for_status()
        product_data = response.json()

        # Sprawdzenie dostępności produktu
        available_quantity = product_data.get('quantity', 0)
        if available_quantity < quantity:
            return jsonify({'message': f'Niewystarczająca ilość produktu ID {product_id} na stanie. Dostępna ilość: {available_quantity}'}), 400
    except requests.exceptions.Timeout:
        current_app.logger.error(f"Przekroczono czas oczekiwania na odpowiedź serwisu produktów dla produktu ID {product_id}")
        return jsonify({'message': 'Serwis produktów jest niedostępny. Spróbuj ponownie później.'}), 503
    except requests.exceptions.RequestException as e:
        current_app.logger.error(f"Błąd podczas weryfikacji produktu ID {product_id}: {e}")
        return jsonify({'message': 'Nie udało się zweryfikować produktu. Spróbuj ponownie później.'}), 500
    except ValueError as e:
        current_app.logger.error(f"Błąd konfiguracji: {e}")
        return jsonify({'message': str(e)}), 500

    user_id = request.user_id  # Pobieranie user_id z tokenu

    # Sprawdź, czy koszyk użytkownika istnieje
    cart = Cart.query.filter_by(user_id=user_id).first()
    if not cart:
        cart = Cart(user_id=user_id)
        db.session.add(cart)
        db.session.commit()

    # Sprawdź, czy produkt już istnieje w koszyku
    cart_item = CartItem.query.filter_by(cart_id=cart.id, product_id=product_id).first()
    if cart_item:
        cart_item.quantity += quantity  # Aktualizuj ilość
    else:
        cart_item = CartItem(cart_id=cart.id, product_id=product_id, quantity=quantity)
        db.session.add(cart_item)

    db.session.commit()
    return jsonify({'message': 'Produkt dodany do koszyka'}), 200




# Wyświetlanie zawartości koszyka
@cart_blueprint.route('/cart', methods=['GET'])
@token_required
def get_cart():
    user_id = request.user_id  # Pobieranie user_id z tokenu

    # Pobieranie koszyka użytkownika
    cart = Cart.query.filter_by(user_id=user_id).first()
    if not cart or not cart.items:
        return jsonify({'cart': []}), 200

    # Zwracanie zawartości koszyka
    cart_items = [
        {'product_id': item.product_id, 'quantity': item.quantity}
        for item in cart.items
    ]
    return jsonify({'cart': cart_items}), 200
