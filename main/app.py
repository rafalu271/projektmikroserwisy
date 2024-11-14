from flask import Flask, render_template, request, redirect, url_for, flash, session
import requests
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, DecimalField, IntegerField
from wtforms.validators import DataRequired, Length, EqualTo, NumberRange
from functools import wraps
import jwt

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'  # Klucz do podpisywania sesji i tokenów
PRODUCT_SERVICE_URL = 'http://localhost:5002/api/products'  # Adres URL mikrousługi produktów

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

# Formularz do dodawania/edycji produktów
class ProductForm(FlaskForm):
    name = StringField('Nazwa', validators=[DataRequired(), Length(min=1, max=100)])
    description = StringField('Opis', validators=[DataRequired(), Length(min=1, max=500)])
    price = DecimalField('Cena', validators=[DataRequired(), NumberRange(min=0)], places=2)
    quantity = IntegerField('Ilość', validators=[DataRequired(), NumberRange(min=0)])
    submit = SubmitField('Zapisz')

@app.route('/')
def index():
    return render_template('index.html')

# Rejestracja użytkownika
@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        registration_data = {
            'username': form.username.data,
            'password': form.password.data
        }
        try:
            response = requests.post('http://localhost:5001/api/register', json=registration_data)
            if response.status_code == 201:
                flash('Rejestracja zakończona sukcesem. Możesz się teraz zalogować.', 'success')
                return redirect(url_for('login'))
            else:
                message = response.json().get('message', 'Błąd rejestracji')
                flash(message, 'danger')
        except requests.exceptions.ConnectionError:
            flash('Nie udało się połączyć z usługą rejestracji.', 'danger')
    return render_template('register.html', form=form)

# Logowanie użytkownika
@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        response = requests.post('http://localhost:5001/api/login', json={'username': username, 'password': password})
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 'success':
                session['token'] = data['token']
                flash('Zalogowano pomyślnie!', 'success')
                return redirect(url_for('index'))
            else:
                flash(data.get('message', 'Błąd logowania'), 'danger')
        else:
            message = response.json().get('message', 'Błąd logowania')
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

# Widoki obsługi katalogu produktów
@app.route('/products')
def show_products():
    try:
        response = requests.get(PRODUCT_SERVICE_URL)
        response.raise_for_status()
        products = response.json()
    except requests.exceptions.RequestException:
        flash("Nie udało się pobrać listy produktów.", 'danger')
        products = []
    
    return render_template('products.html', products=products)

@app.route('/products/add', methods=['GET', 'POST'])
def add_product():
    form = ProductForm()  # Tworzymy instancję formularza
    if form.validate_on_submit():
        new_product = {
            'name': form.name.data,
            'description': form.description.data,
            'price': float(form.price.data), # Konwertujemy cenę na float
            'quantity': int(form.quantity.data)  # Zapewniamy, że ilość jest liczbą całkowitą
        }
        try:
            response = requests.post(PRODUCT_SERVICE_URL, json=new_product)
            response.raise_for_status()
            flash('Produkt został dodany!', 'success')
            return redirect(url_for('show_products'))
        except requests.exceptions.RequestException:
            flash("Nie udało się dodać produktu.", 'danger')
    
    return render_template('product_form.html', form=form, product=None)

@app.route('/products/edit/<int:product_id>', methods=['GET', 'POST', 'PUT'])
def edit_product(product_id):
    form = ProductForm()  # Tworzymy instancję formularza
    if form.validate_on_submit():
        # Konwertowanie typów danych przed wysłaniem
        updated_product = {
            'name': form.name.data,
            'description': form.description.data,
            'price': float(form.price.data),  # Konwertujemy cenę na float
            'quantity': int(form.quantity.data)  # Zapewniamy, że ilość jest liczbą całkowitą
        }
        try:
            response = requests.put(f"{PRODUCT_SERVICE_URL}/{product_id}", json=updated_product)
            response.raise_for_status()
            flash('Produkt został zaktualizowany!', 'success')
            return redirect(url_for('show_products'))
        except requests.exceptions.RequestException:
            flash("Nie udało się zaktualizować produktu.", 'danger')
    else:
        try:
            response = requests.get(f"{PRODUCT_SERVICE_URL}/{product_id}")
            response.raise_for_status()
            product = response.json()
            # Ustawianie danych w formularzu
            form.name.data = product['name']
            form.description.data = product['description']
            form.price.data = product['price']
            form.quantity.data = product['quantity']
        except requests.exceptions.RequestException:
            flash("Nie udało się pobrać szczegółów produktu.", 'danger')
            return redirect(url_for('show_products'))
        
    return render_template('product_form.html', form=form, product=product)

@app.route('/products/delete/<int:product_id>', methods=['POST'])
def delete_product(product_id):
    try:
        response = requests.delete(f"{PRODUCT_SERVICE_URL}/{product_id}")
        response.raise_for_status()
        flash('Produkt został usunięty!', 'success')
    except requests.exceptions.RequestException:
        flash("Nie udało się usunąć produktu.", 'danger')
    
    return redirect(url_for('show_products'))

if __name__ == '__main__':
    app.run(debug=True)
