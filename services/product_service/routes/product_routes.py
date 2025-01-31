from flask import Blueprint, jsonify, request
from models.product import Product
from db import db
import pika
import json

product_blueprint = Blueprint('product_blueprint', __name__)

def send_notification_to_rabbitmq(queue_name, message):
    """Wysyła powiadomienie do RabbitMQ."""
    try:
        connection = pika.BlockingConnection(
            pika.ConnectionParameters(
                host='rabbitmq',
                credentials=pika.PlainCredentials('guest', 'guest')
            )
        )
        channel = connection.channel()

        # Deklaracja kolejki
        channel.queue_declare(queue=queue_name)

        # Publikacja wiadomości
        channel.basic_publish(
            exchange='',
            routing_key=queue_name,
            body=json.dumps(message)
        )
        connection.close()
    except Exception as e:
        print(f"Błąd wysyłania powiadomienia do RabbitMQ: {e}")


# Pobieranie wszystkich produktów
@product_blueprint.route('/', methods=['GET'])
def get_products():
    products = Product.query.all()
    return jsonify([product.to_dict() for product in products]), 200

# Pobieranie pojedynczego produktu
@product_blueprint.route('/<int:product_id>', methods=['GET'])
def get_product(product_id):
    product = Product.query.get(product_id)
    if not product:
        return jsonify({'message': 'Produkt nie znaleziony'}), 404
    return jsonify(product.to_dict()), 200

# Dodawanie nowego produktu
@product_blueprint.route('/', methods=['POST'])
def add_product():
    data = request.get_json()
    new_product = Product(
        name=data.get('name'),
        description=data.get('description'),
        price=data.get('price'),
        quantity=data.get('quantity')
    )
    db.session.add(new_product)
    db.session.commit()

    # Przygotowanie wiadomości powiadomienia
    notification_message = {
        'event': 'product_added',
        'product_id': new_product.id,
        'name': new_product.name,
        'description': new_product.description,
        'price': new_product.price,
        'quantity': new_product.quantity
    }
    
    # Wysyłanie powiadomienia do RabbitMQ
    send_notification_to_rabbitmq('notifications', notification_message)

    return jsonify(new_product.to_dict()), 201

# Aktualizacja istniejącego produktu
@product_blueprint.route('/<int:product_id>', methods=['PUT'])
def update_product(product_id):
    product = Product.query.get(product_id)
    if not product:
        return jsonify({'message': 'Produkt nie znaleziony'}), 404
    
    data = request.get_json()
    product.name = data.get('name', product.name)
    product.description = data.get('description', product.description)
    product.price = data.get('price', product.price)
    product.quantity = data.get('quantity', product.quantity)

    db.session.commit()
    return jsonify(product.to_dict()), 200

# Usuwanie produktu
@product_blueprint.route('/<int:product_id>', methods=['DELETE'])
def delete_product(product_id):
    product = Product.query.get(product_id)
    if not product:
        return jsonify({'message': 'Produkt nie znaleziony'}), 404

    db.session.delete(product)
    db.session.commit()
    return jsonify({'message': 'Produkt usunięty'}), 200
