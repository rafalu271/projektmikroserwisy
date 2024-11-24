from flask import Flask
from db import db
from routes.product_routes import product_blueprint
from config import Config
import py_eureka_client.eureka_client as eureka_client

# Konfiguracja klienta Eureka
eureka_client.init(eureka_server="http://172.28.0.12:8761,",
                                app_name="product_service",
                                instance_port=5002)

# Rejestracja w Eureka
eureka_client.register()

app = Flask(__name__)
app.config.from_object(Config)

# Inicjalizacja bazy danych
db.init_app(app)

# Rejestracja blueprintu z endpointami produktów
app.register_blueprint(product_blueprint, url_prefix='/api/products')

if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Tworzy tabelę produktów, jeśli nie istnieje
    app.run(debug=True, host='0.0.0.0', port=5002)
