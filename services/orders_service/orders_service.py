from flask import Flask, request, jsonify
from db import db
from routes import cart_blueprint, order_blueprint
from config import Config
import jwt
from functools import wraps
import consul
import os

# Dodanie do Consul
def register_service_with_consul():
    consul_client = consul.Consul(host=os.getenv('CONSUL_HOST', 'consul-server'), port=int(os.getenv('CONSUL_PORT', 8500)))
    
    service_id = "orders_service_id"  # Unikalny identyfikator dla Twojej usługi

    # Sprawdź, czy usługa już istnieje i ją wyrejestruj przed ponownym rejestrowaniem
    consul_client.agent.service.deregister(service_id)
        
    # Rejestracja usługi
    service_name = "orders_service"
    service_id = f"{service_name}-{os.getenv('HOSTNAME', 'local')}"
    service_port = int(os.getenv('SERVICE_PORT', 5003))

    consul_client.agent.service.register(
        name=service_name,
        service_id=service_id,
        address=os.getenv('SERVICE_HOST', 'orders_service'),  # Użyj nazwy kontenera Dockera
        port=service_port,
        tags=[
            "traefik.enable=true",
            f"traefik.http.routers.orders_service.rule=Host(`orders_service`) && (PathPrefix(`/cart`) || PathPrefix(`/orders`) || PathPrefix(`/checkout`))",
            "traefik.http.services.orders_service.loadbalancer.server.scheme=http",
            f"traefik.http.services.orders_service.loadbalancer.server.port={service_port}",
            "flask"
        ]
    )
    print(f"Zarejestrowano usługę {service_name} w Consul")

app = Flask(__name__)
app.config.from_object(Config)

# Inicjalizacja bazy danych
db.init_app(app)

# Tworzenie tabel w bazie danych
with app.app_context():
    db.create_all()  # Tworzy tabele na podstawie modeli

# Dekorator do weryfikacji tokenów JWT
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization', '').split("Bearer ")[-1]  # Pobranie tokenu z nagłówka
        if not token:
            return jsonify({'message': 'Brak tokenu, dostęp zabroniony!'}), 401
        try:
            # Weryfikacja tokenu JWT
            decoded_token = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
            # Możesz dodać dane użytkownika do requestu, jeśli jest to potrzebne
            request.user = decoded_token
        except jwt.ExpiredSignatureError:
            return jsonify({'message': 'Token wygasł!'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'message': 'Nieprawidłowy token!'}), 403
        return f(*args, **kwargs)
    return decorated


# Rejestracja blueprintów
app.register_blueprint(cart_blueprint, url_prefix='/api')
app.register_blueprint(order_blueprint, url_prefix='/api')


# Przykładowe zabezpieczenie endpointów w blueprintach
@app.route('/api/protected', methods=['GET'])
@token_required
def protected_route():
    return jsonify({'message': 'Dostęp uzyskany do chronionego zasobu!'})


if __name__ == '__main__':
    # Rejestracja usługi w Consul
    register_service_with_consul()

    app.run(debug=True, host='0.0.0.0', port=5003)  # Przykładowo na porcie 5003
