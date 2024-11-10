# app.py
from flask import Flask, render_template, request, redirect, url_for, flash, session
import requests
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Length, EqualTo
from functools import wraps
import jwt

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'  # Klucz do podpisywania sesji i tokenów

# Formularz rejestracji
class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=4, max=150)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Register')

# Formularz logowania
class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

@app.route('/')
def index():
    return render_template('index.html')

# Rejestracja użytkownika
@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        # Wysłanie danych rejestracyjnych do mikrousługi
        registration_data = {
            'username': form.username.data,
            'password': form.password.data
        }
        try:
            # Żądanie do mikrousługi rejestracji
            response = requests.post('http://localhost:5001/api/register', json=registration_data)

            if response.status_code == 201:
                flash('Rejestracja zakończona sukcesem. Możesz się teraz zalogować.', 'success')
                return redirect(url_for('login'))
            else:
                try:
                    # Próba parsowania odpowiedzi JSON
                    message = response.json().get('message', 'Błąd rejestracji')
                except ValueError:
                    # Jeśli odpowiedź nie jest w formacie JSON
                    message = 'Błąd po stronie serwera'
                flash(message, 'danger')

        except requests.exceptions.ConnectionError:
            flash('Nie udało się połączyć z usługą rejestracji.', 'danger')
    return render_template('register.html', form=form)

# Logowanie użytkownika
@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()  # Tworzymy instancję formularza
    
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Wysyłanie żądania do mikroserwisu logowania
        response = requests.post('http://localhost:5001/api/login', json={
            'username': username,
            'password': password
        })

        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 'success':
                # Zapisanie tokenu w sesji
                session['token'] = data['token']
                flash('Zalogowano pomyślnie!', 'success')
                return redirect(url_for('index'))
            else:
                flash(data.get('message', 'Błąd logowania'), 'danger')
        else:
            try:
                # Jeśli odpowiedź nie jest JSON, przekaż wiadomość
                message = response.json().get('message', 'Błąd logowania')
            except ValueError:
                # Jeśli odpowiedź nie jest w formacie JSON
                message = 'Błąd po stronie serwera'
            flash(message, 'danger')

    return render_template('login.html', form=form)

# Logika do wymagania logowania
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = session.get('token')
        if not token:
            flash('Zaloguj się, aby uzyskać dostęp', 'danger')
            return redirect(url_for('login'))
        
        try:
            # Sprawdzanie poprawności tokenu
            jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
        except jwt.ExpiredSignatureError:
            flash('Twoja sesja wygasła, zaloguj się ponownie', 'danger')
            return redirect(url_for('login'))
        except jwt.InvalidTokenError:
            flash('Nieprawidłowy token', 'danger')
            return redirect(url_for('login'))

        return f(*args, **kwargs)
    return decorated_function

# Wymagane logowanie
@app.route('/some_protected_route')
@login_required
def protected_route():
    return "Zawartość dostępna tylko dla zalogowanych użytkowników"

if __name__ == '__main__':
    app.run(debug=True)
