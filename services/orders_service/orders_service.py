from flask import Flask
from db import db
from routes import cart_blueprint, order_blueprint
from config import Config

app = Flask(__name__)
app.config.from_object(Config)

# Inicjalizacja bazy danych
db.init_app(app)

# Rejestracja blueprintów
app.register_blueprint(cart_blueprint, url_prefix='/api')
app.register_blueprint(order_blueprint, url_prefix='/api')

if __name__ == '__main__':
    app.run(debug=True, port=5003)  # Przykładowo na porcie 5001

