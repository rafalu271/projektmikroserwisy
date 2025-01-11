from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
import datetime
import consul
import os
import pika
import json

# Dodanie do Consul z Traefik
def register_service_with_consul():
    consul_client = consul.Consul(host=os.getenv('CONSUL_HOST', 'consul-server'), port=int(os.getenv('CONSUL_PORT', 8500)))
    
    service_id = "registration_service_id"  # Unikalny identyfikator dla Twojej usługi

    # Sprawdź, czy usługa już istnieje i ją wyrejestruj przed ponownym rejestrowaniem
    consul_client.agent.service.deregister(service_id)
        
    # Rejestracja usługi
    service_name = "registration_service"
    service_id = f"{service_name}-{os.getenv('HOSTNAME', 'local')}"
    service_port = int(os.getenv('SERVICE_PORT', 5001))

    consul_client.agent.service.register(
        name=service_name,
        service_id=service_id,
        address=os.getenv('SERVICE_HOST', 'registration_service'),  # Użyj nazwy kontenera Dockera
        port=service_port,
        tags=[
            "traefik.enable=true",
            f"traefik.http.routers.registration_service.rule=(PathPrefix(`/api/register`) || PathPrefix(`/api/login`))",
            "traefik.http.services.registration_service.loadbalancer.server.scheme=http",
            f"traefik.http.services.registration_service.loadbalancer.server.port={service_port}",
            "flask"
        ]
    )
    print(f"Zarejestrowano usługę {service_name} w Consul")

# Funkcja do wysyłania wiadomości RabbitMQ
def publish_message(queue_name, message):
    try:
        connection = pika.BlockingConnection(pika.ConnectionParameters(host='rabbitmq'))
        channel = connection.channel()
        channel.queue_declare(queue=queue_name)
        channel.basic_publish(exchange='', routing_key=queue_name, body=json.dumps(message))
        connection.close()
        print(f"Wiadomość wysłana do kolejki '{queue_name}': {message}")
    except Exception as e:
        print(f"Błąd podczas wysyłania wiadomości RabbitMQ: {str(e)}")

app = Flask(__name__)
app.config['SECRET_KEY'] = 'super_secret_key'

# Konfiguracja bazy danych SQLite
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Inicjalizacja SQLAlchemy
db = SQLAlchemy(app)

# Model użytkownika
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)

# Tworzenie tabeli użytkowników (jeśli nie istnieje)
with app.app_context():
    db.create_all()

@app.route('/api/register', methods=['POST'])
def register_user():
    data = request.get_json()

    # Sprawdzenie, czy dane zostały wysłane
    if not data or 'username' not in data or 'password' not in data:
        return jsonify({'status': 'error', 'message': 'Brak wymaganych danych (username, password)'}), 400

    username = data['username']
    password = data['password']
    
    # Sprawdzanie, czy użytkownik już istnieje
    existing_user = User.query.filter_by(username=username).first()
    
    if existing_user:
        return jsonify({'status': 'error', 'message': 'Użytkownik już istnieje'}), 400
    
    # Tworzenie nowego użytkownika
    hashed_password = generate_password_hash(password)
    new_user = User(username=username, password=hashed_password)
    
    try:
        db.session.add(new_user)
        db.session.commit()

        # Wysłanie wiadomości RabbitMQ
        message = {
            'event': 'user_registered',
            'user_id': new_user.id,
            'username': new_user.username
        }
        publish_message('notifications', message)

    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': f'Błąd przy rejestracji: {str(e)}'}), 500
    
    return jsonify({'status': 'success', 'message': 'Użytkownik zarejestrowany pomyślnie'})

@app.route('/api/login', methods=['POST'])
def login_user():
    data = request.get_json()
    
    if not data or 'username' not in data or 'password' not in data:
        return jsonify({'status': 'error', 'message': 'Brak danych logowania'}), 400
    
    username = data.get('username')
    password = data.get('password')

    # Sprawdzenie, czy użytkownik istnieje w bazie
    user = User.query.filter_by(username=username).first()
    
    if user and check_password_hash(user.password, password):  # Sprawdzanie hasła
        # Generowanie tokenu JWT
        token = jwt.encode(
            {
                'user_id': user.id,  # Używamy user_id zamiast username
                'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=1)
            },
            app.config['SECRET_KEY'],
            algorithm='HS256'
        )

        return jsonify({'status': 'success', 'message': 'Zalogowano pomyślnie', 'token': token})
    
    return jsonify({'status': 'error', 'message': 'Błędna nazwa użytkownika lub hasło'}), 401

if __name__ == '__main__':
    # Rejestracja usługi w Consul
    register_service_with_consul()

    app.run(debug=True, host='0.0.0.0', port=5001)
