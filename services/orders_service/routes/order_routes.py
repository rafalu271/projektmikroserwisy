from flask import Blueprint, jsonify, request, current_app
from db import db
from models import Order, OrderItem, Cart, CartItem
import requests
import pika
import json

order_blueprint = Blueprint('order_blueprint', __name__)

def get_product_service_url():
    """Funkcja pomocnicza do pobierania URL serwisu produktów"""
    product_service_url = current_app.config.get('PRODUCT_SERVICE_URL')
    if not product_service_url:
        raise ValueError("Nie można znaleźć URL serwisu produktów.")
    return product_service_url

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

# Funkcja wysyłająca powiadomienia do RabbitMQ
def send_notification_to_rabbitmq(queue_name, message):
    try:
        connection = pika.BlockingConnection(
            pika.ConnectionParameters(
                host='rabbitmq',
                credentials=pika.PlainCredentials('guest', 'guest')
            )
        )
        channel = connection.channel()
        channel.queue_declare(queue=queue_name)
        channel.basic_publish(exchange='', routing_key=queue_name, body=json.dumps(message))
        connection.close()
        current_app.logger.info(f"Wysłano powiadomienie do kolejki '{queue_name}': {message}")
    except Exception as e:
        current_app.logger.error(f"Błąd wysyłania powiadomienia do RabbitMQ: {e}")

# Proces składania zamówienia
@order_blueprint.route('/orders/checkout', methods=['POST'])
def checkout():
    data = request.get_json()
    user_id = data.get('user_id')

    if not user_id:
        return jsonify({'message': 'Brak user_id'}), 400

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

    # Wysłanie powiadomienia do RabbitMQ
    notification_message = {
        'event': 'order_created',
        'order_id': order.id,
        'user_id': user_id,
        'total_price': total_price,
        'status': order.status
    }
    send_notification_to_rabbitmq('notifications', notification_message)

    return jsonify({'message': 'Zamówienie zostało złożone', 'order_id': order.id}), 201

# Wyświetlanie szczegółów zamówienia
@order_blueprint.route('/order/<int:order_id>', methods=['POST'])
def get_order(order_id):
    data = request.get_json()
    user_id = data.get('user_id')

    if not user_id:
        return jsonify({'message': 'Brak user_id'}), 400

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
@order_blueprint.route('/orders', methods=['POST'])
def get_orders():
    data = request.get_json()
    user_id = data.get('user_id')

    if not user_id:
        return jsonify({'message': 'Brak user_id'}), 400

    try:
        # Pobieranie zamówień użytkownika
        orders = Order.query.filter_by(user_id=user_id).all()

        # Serializacja zamówień
        serialized_orders = []
        for order in orders:
            try:
                serialized_order = {
                    'id': order.id,
                    'user_id': order.user_id,
                    'total_price': order.total_price,
                    'status': order.status,
                    'items': [
                        {'product_id': item.product_id, 'quantity': item.quantity}
                        for item in order.order_items
                    ]
                }
                serialized_orders.append(serialized_order)
            except AttributeError as e:
                current_app.logger.error(f"Błąd przetwarzania zamówienia ID {order.id}: {e}")
                continue

        return jsonify(serialized_orders), 200

    except Exception as e:
        current_app.logger.error(f"Błąd podczas pobierania zamówień: {e}")
        return jsonify({'message': 'Nie udało się pobrać historii zamówień.'}), 500
