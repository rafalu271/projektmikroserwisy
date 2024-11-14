from flask import Flask
from db import db
from routes.product_routes import product_blueprint
from config import Config

app = Flask(__name__)
app.config.from_object(Config)

# Inicjalizacja bazy danych
db.init_app(app)

# Rejestracja blueprintu z endpointami produktów
app.register_blueprint(product_blueprint, url_prefix='/api/products')

if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Tworzy tabelę produktów, jeśli nie istnieje
    app.run(port=5002, debug=True)
