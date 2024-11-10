# registration_service.py
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from models import User
import jwt
import datetime

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

@app.route('/register', methods=['POST'])
def register_user():
    data = request.json
    username = data.get('username')
    password = data.get('password')

    # Sprawdzanie, czy użytkownik już istnieje
    if User.query.filter_by(username=username).first():
        return jsonify({'message': 'Username already exists'}), 400

    # Hashowanie hasła i dodanie użytkownika do bazy
    hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
    new_user = User(username=username, password=hashed_password)
    db.session.add(new_user)
    db.session.commit()

    return jsonify({'message': 'User registered successfully'}), 201

@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    user = User.query.filter_by(username=username).first()
    if user and check_password_hash(user.password, password):
        # Tworzenie tokenu JWT
        token = jwt.encode({
            'user_id': user.id,
            'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=1)
        }, app.config['SECRET_KEY'], algorithm='HS256')
        
        return jsonify({'status': 'success', 'token': token})
    
    return jsonify({'status': 'error', 'message': 'Invalid username or password'}), 401

if __name__ == '__main__':
    app.run(port=5001, debug=True)
