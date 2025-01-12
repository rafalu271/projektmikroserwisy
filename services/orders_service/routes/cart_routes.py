from flask import Blueprint, jsonify, request, current_app
from db import db
from models import Cart, CartItem
import requests

cart_blueprint = Blueprint('cart_blueprint', __name__)

def get_product_service_url():
    """Funkcja pomocnicza do pobierania URL serwisu produktów"""
    product_service_url = current_app.config.get('PRODUCT_SERVICE_URL')
    if not product_service_url:
        raise ValueError("Nie można znaleźć URL serwisu produktów.")
    return product_service_url


# Wyświetlanie zawartości koszyka
@cart_blueprint.route('/cart', methods=['GET', 'POST'])
def get_cart():
    data = request.get_json()
    user_id = data.get('user_id')  # Pobieranie user_id z JSON

    if not user_id:
        return jsonify({'message': 'Brak user_id'}), 400

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


# Dodawanie produktów do koszyka
@cart_blueprint.route('/cart/add', methods=['POST'])
def add_to_cart():
    data = request.get_json()
    user_id = data.get('user_id')
    product_id = data.get('product_id')
    quantity = data.get('quantity', 1)

    if not user_id or not product_id:
        return jsonify({'message': 'Brak user_id lub ID produktu'}), 400

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


# Usuwanie produktów z koszyka
@cart_blueprint.route('/cart/remove', methods=['POST'])
def remove_from_cart():
    data = request.get_json()
    user_id = data.get('user_id')
    product_id = data.get('product_id')

    if not user_id or not product_id:
        return jsonify({'message': 'Brak user_id lub ID produktu'}), 400

    try:
        # Pobranie koszyka użytkownika
        cart = Cart.query.filter_by(user_id=user_id).first()
        if not cart:
            return jsonify({'message': 'Koszyk użytkownika nie istnieje'}), 404

        # Sprawdzenie, czy produkt znajduje się w koszyku
        cart_item = CartItem.query.filter_by(cart_id=cart.id, product_id=product_id).first()
        if not cart_item:
            return jsonify({'message': f'Produkt ID {product_id} nie znajduje się w koszyku'}), 404

        # Usunięcie produktu z koszyka
        db.session.delete(cart_item)
        db.session.commit()

        return jsonify({'message': f'Produkt ID {product_id} został usunięty z koszyka'}), 200

    except Exception as e:
        current_app.logger.error(f"Błąd podczas usuwania produktu ID {product_id} z koszyka: {e}")
        return jsonify({'message': 'Wystąpił błąd podczas usuwania produktu z koszyka'}), 500


# Aktualizacja ilości produktów w koszyku
@cart_blueprint.route('/cart/update', methods=['POST'])
def update_cart():
    data = request.get_json()
    user_id = data.get('user_id')
    product_id = data.get('product_id')
    quantity = data.get('quantity')

    if not user_id or not product_id or quantity is None:
        return jsonify({'message': 'Brak user_id, ID produktu lub ilości'}), 400

    if quantity <= 0:
        return jsonify({'message': 'Ilość produktu musi być większa niż zero'}), 400

    try:
        # Pobranie koszyka użytkownika
        cart = Cart.query.filter_by(user_id=user_id).first()
        if not cart:
            return jsonify({'message': 'Koszyk użytkownika nie istnieje'}), 404

        # Sprawdzenie, czy produkt znajduje się w koszyku
        cart_item = CartItem.query.filter_by(cart_id=cart.id, product_id=product_id).first()
        if not cart_item:
            return jsonify({'message': f'Produkt ID {product_id} nie znajduje się w koszyku'}), 404

        # Aktualizacja ilości produktu
        cart_item.quantity = quantity
        db.session.commit()

        return jsonify({'message': f'Ilość produktu ID {product_id} została zaktualizowana na {quantity}'}), 200

    except Exception as e:
        current_app.logger.error(f"Błąd podczas aktualizacji ilości produktu ID {product_id} w koszyku: {e}")
        return jsonify({'message': 'Wystąpił błąd podczas aktualizacji ilości produktu w koszyku'}), 500
