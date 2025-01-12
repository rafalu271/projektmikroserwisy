from flask import Flask, request, jsonify
import consul
import os
import pika
import json
import threading
import logging
import sys

# Konfiguracja loggera
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    stream=sys.stdout,
    force=True,
)

app = Flask(__name__)

# Rejestracja usługi powiadomień w Consul
def register_service_with_consul():
    try:
        consul_client = consul.Consul(host=os.getenv('CONSUL_HOST', 'consul-server'), port=int(os.getenv('CONSUL_PORT', 8500)))
        
        service_name = "notification_service"
        service_id = f"{service_name}-{os.getenv('HOSTNAME', 'local')}"
        service_port = int(os.getenv('SERVICE_PORT', 5005))

        # Wyrejestrowanie, jeśli istnieje
        consul_client.agent.service.deregister(service_id)

        # Rejestracja usługi
        consul_client.agent.service.register(
            name=service_name,
            service_id=service_id,
            address=os.getenv('SERVICE_HOST', 'notification_service'),
            port=service_port,
            tags=[
                "traefik.enable=true",
                f"traefik.http.routers.{service_name}.rule=PathPrefix(`/notifications`)",
                "traefik.http.services.notification_service.loadbalancer.server.scheme=http",
                f"traefik.http.services.notification_service.loadbalancer.server.port={service_port}",
                "flask"
            ]
        )
        logging.info(f"Zarejestrowano usługę {service_name} w Consul")
    except Exception as e:
        logging.error(f"Błąd rejestracji usługi w Consul: {e}")

# Funkcja obsługująca wiadomości RabbitMQ
def consume_notifications():
    """Nasłuchuje na kolejce 'notifications' i przetwarza wiadomości."""
    while True:
        try:
            logging.info("Próba połączenia z RabbitMQ...")
            connection = pika.BlockingConnection(
                pika.ConnectionParameters(
                    host='rabbitmq',
                    credentials=pika.PlainCredentials('guest', 'guest')
                )
            )
            channel = connection.channel()

            # Deklaracja kolejki
            channel.queue_declare(queue='notifications')

            # Funkcja obsługująca wiadomości
            def on_message(ch, method, properties, body):
                try:
                    message = json.loads(body.decode('utf-8'))
                    logging.info(f"Otrzymano powiadomienie: {message}")
                except json.JSONDecodeError as e:
                    logging.error(f"Błąd dekodowania wiadomości: {e}")

            # Nasłuchiwanie na kolejce
            channel.basic_consume(queue='notifications', on_message_callback=on_message, auto_ack=True)
            logging.info("Serwis powiadomień działa i nasłuchuje...")
            channel.start_consuming()

        except pika.exceptions.AMQPConnectionError as e:
            logging.error(f"RabbitMQ niedostępne: {e}. Ponawianie za 5 sekund...")
            time.sleep(5)

@app.route('/notifications', methods=['POST'])
def send_notification():
    data = request.get_json()
    notification_type = data.get('type', 'generic')  # email, sms, etc.
    message = data.get('message', 'Brak treści powiadomienia')

    # Symulacja wysyłania powiadomienia
    logging.info(f"Symulacja powiadomienia [{notification_type.upper()}]: {message}")

    return jsonify({'message': 'Powiadomienie zostało wysłane'}), 200

if __name__ == '__main__':
    # Rejestracja w Consul
    register_service_with_consul()

    # Uruchomienie konsumenta RabbitMQ w osobnym wątku
    consumer_thread = threading.Thread(target=consume_notifications, daemon=True)
    consumer_thread.start()

    # Uruchomienie serwera Flask
    app.run(debug=True, host='0.0.0.0', port=5005)
