from flask import Flask, request, jsonify
from db import db
from routes import cart_blueprint, order_blueprint
from config import Config
import jwt
from functools import wraps

app = Flask(__name__)
app.config.from_object(Config)

# Inicjalizacja bazy danych
db.init_app(app)


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
    app.run(debug=True, port=5003)  # Przykładowo na porcie 5003
