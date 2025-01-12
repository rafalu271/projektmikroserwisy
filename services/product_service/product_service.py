from flask import Flask
from db import db
from routes.product_routes import product_blueprint
from config import Config
import consul
import os

# Rejestracja usługi z Consul
def register_service_with_consul():
    consul_client = consul.Consul(host=os.getenv('CONSUL_HOST', 'consul-server'), port=int(os.getenv('CONSUL_PORT', 8500)))
    
    service_id = "product_service_id"  # Unikalny identyfikator dla usługi

    # Wyrejestrowanie przed ponownym rejestrowaniem
    consul_client.agent.service.deregister(service_id)
        
    # Rejestracja usługi
    service_name = "product_service"
    service_id = f"{service_name}-{os.getenv('HOSTNAME', 'local')}"
    service_port = int(os.getenv('SERVICE_PORT', 5002))

    consul_client.agent.service.register(
        name=service_name,
        service_id=service_id,
        address=os.getenv('SERVICE_HOST', 'product_service'),
        port=service_port,
        tags=[
            "traefik.enable=true",
            f"traefik.http.routers.product_service.rule=PathPrefix(`/products`)",
            "traefik.http.services.product_service.loadbalancer.server.scheme=http",
            f"traefik.http.services.product_service.loadbalancer.server.port={service_port}",
            "flask"
        ]
    )
    print(f"Zarejestrowano usługę {service_name} w Consul")


app = Flask(__name__)
app.config.from_object(Config)

# Inicjalizacja bazy danych
db.init_app(app)

app.register_blueprint(product_blueprint, url_prefix='/products')


@app.route('/health', methods=["GET"])
def health():
    return "OK", 200


if __name__ == '__main__':
    # Rejestracja usługi z Consul
    register_service_with_consul()

    with app.app_context():
        db.create_all()
    app.run(debug=True, host='0.0.0.0', port=5002)
