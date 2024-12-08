from flask import Flask
from db import db
from routes.product_routes import product_blueprint
from config import Config
import consul
import os

# Rejestracja usługi z Consul
def register_service_with_consul():
    consul_client = consul.Consul(host=os.getenv('CONSUL_HOST', 'consul-server'), port=os.getenv('CONSUL_PORT', 8500))
    
    service_id = "product_service_id"

    # Sprawdzenie, czy usługa istnieje i jej usunięcie
    consul_client.agent.service.deregister(service_id)

    service_name = "product_service"
    service_id = f"{service_name}-{os.getenv('HOSTNAME', 'local')}"
    service_port = 5002

    endpoints = [
        "/api/products",
        "/api/products/<id>",
        "/api/products/search",
    ]

    # Rejestracja usługi z health check
    consul_client.agent.service.register(
        name=service_name,
        service_id=service_id,
        address=os.getenv('SERVICE_HOST', '127.0.0.1'),
        port=service_port,
        tags=["flask", "product_service"] + endpoints,
        check=consul.Check.http("http://localhost:5002/health", interval="10s")
    )
    print(f"Zarejestrowano usługę {service_name} z endpointami i health check w Consul")


app = Flask(__name__)
app.config.from_object(Config)

# Inicjalizacja bazy danych
db.init_app(app)

# Rejestracja blueprintu z endpointami produktów
app.register_blueprint(product_blueprint, url_prefix='/api/products')


@app.route('/health', methods=["GET"])
def health():
    return "OK", 200


if __name__ == '__main__':
    # Rejestracja usługi z Consul
    register_service_with_consul()

    with app.app_context():
        db.create_all()  # Tworzy tabelę produktów, jeśli nie istnieje
    app.run(debug=True, host='0.0.0.0', port=5002)
