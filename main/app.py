from flask import Flask, render_template, request, redirect, url_for, flash, session
import requests
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, DecimalField, IntegerField
from wtforms.validators import DataRequired, Length, EqualTo, NumberRange
from functools import wraps
import jwt
from dotenv import load_dotenv
import os

# Załadowanie zmiennych z pliku .env
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')  # Klucz do podpisywania sesji i tokenów
PRODUCT_SERVICE_URL = 'http://localhost:5002/api/products'  # Adres URL mikrousługi produktów

# URL do usługi koszyka i zamówień
CART_SERVICE_URL = 'http://localhost:5003/api/cart'
ORDER_SERVICE_URL = 'http://localhost:5003/api/orders'

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

# Funkcja pomocnicza do dodawania tokenu w nagłówkach
def add_auth_headers(headers=None):
    if headers is None:
        headers = {}
    token = session.get('token')
    if token:
        headers['Authorization'] = f"Bearer {token}"
    return headers

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
                try:
                    message = response.json().get('message', 'Błąd rejestracji')
                except requests.exceptions.JSONDecodeError:
                    message = 'Niepoprawny format odpowiedzi serwera podczas rejestracji.'
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
        try:
            response = requests.post('http://localhost:5001/api/login', json={'username': username, 'password': password})
            if response.status_code == 200:
                data = response.json()
                print("Zwrócony token:", data['token'])  # Debugowanie tokenu
                session['token'] = data['token']
                flash('Zalogowano pomyślnie!', 'success')
                return redirect(url_for('index'))
            else:
                message = response.json().get('message', 'Błąd logowania')
                flash(message, 'danger')
        except requests.exceptions.ConnectionError:
            flash('Nie udało się połączyć z usługą logowania.', 'danger')
    return render_template('login.html', form=form)

# Wylogowanie użytkownika
@app.route('/logout')
def logout():
    session.pop('token', None)  # Usuwamy token z sesji
    flash('Zostałeś wylogowany.', 'success')
    return redirect(url_for('index'))

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

@app.route('/products/<int:product_id>', methods=['GET'])
def show_product(product_id):
    try:
        # Wysłanie zapytania do serwisu produktów w celu pobrania szczegółów produktu
        response = requests.get(f"{PRODUCT_SERVICE_URL}/{product_id}")
        response.raise_for_status()  # Sprawdzamy, czy zapytanie się powiodło
        product = response.json()  # Otrzymujemy dane produktu w formacie JSON
    except requests.exceptions.RequestException:
        flash("Nie udało się pobrać szczegółów produktu.", 'danger')
        product = None
    
    # Renderowanie strony z danymi produktu
    return render_template('product_detail.html', product=product)


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

@app.route('/cart')
@login_required
def view_cart():
    try:
        # Pobranie tokenu z sesji
        token = session.get('token')
        username = None
        user_id = None

        if token:
            try:
                # Dekodowanie tokenu JWT
                decoded_token = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
                print("Decoded token:", decoded_token)  # Debugowanie tokenu
                username = decoded_token.get('username')  # Pobranie username z tokenu
                user_id = decoded_token.get('user_id')
            except jwt.ExpiredSignatureError:
                flash("Token wygasł, proszę się zalogować ponownie.", 'danger')
            except jwt.InvalidTokenError:
                flash("Nieprawidłowy token, proszę spróbować ponownie.", 'danger')
        else:
            flash("Brak tokenu autoryzacyjnego, proszę się zalogować.", 'danger')

        # Pobranie danych o koszyku
        headers = add_auth_headers()  # Funkcja do dodawania nagłówków autoryzacji, jeśli to konieczne
        print("Nagłówki wysyłane do serwisu koszyka:", headers)
        response = requests.get(CART_SERVICE_URL, headers=headers)
        response.raise_for_status()  # Jeśli odpowiedź jest błędna, zostanie zgłoszony wyjątek

        # Debugging: sprawdzenie, czy odpowiedź jest w formacie JSON
        try:
            cart_data = response.json()  # Cała odpowiedź
            cart_items = cart_data.get('cart', [])  # Pobieramy listę przedmiotów z klucza 'cart'
        except ValueError:
            flash("Błąd przetwarzania odpowiedzi JSON z serwisu koszyka.", 'danger')
            cart_items = []

        # Debugowanie odpowiedzi koszyka
        print("Odpowiedź koszyka:", cart_data)
        print("Przedmioty w koszyku:", cart_items)

        # Weryfikacja danych koszyka
        if not isinstance(cart_items, list):
            flash("Błąd w formacie danych koszyka.", 'danger')
            cart_items = []

        # Stworzenie kopii koszyka, aby nie modyfikować oryginalnej listy
        updated_cart_items = []
        for item in cart_items:
            product_id = item.get('product_id')
            if not product_id:
                print(f"Błąd: Produkt nie zawiera ID: {item}")
                continue  # Pomijamy przedmioty bez ID produktu

            try:
                # Wykonaj zapytanie do serwisu produktów, aby pobrać szczegóły produktu
                product_response = requests.get(f"{PRODUCT_SERVICE_URL}/{product_id}")
                product_response.raise_for_status()  # Jeżeli odpowiedź jest błędna, zgłosi wyjątek
                product_details = product_response.json()

                # Debugowanie szczegółów produktu
                print(f"Produkt {product_id} szczegóły:", product_details)

                # Dodanie szczegółów produktu do przedmiotu w kopii koszyka
                updated_item = item.copy()  # Tworzymy kopię przedmiotu
                updated_item['product_details'] = product_details
                updated_cart_items.append(updated_item)  # Dodajemy zaktualizowany przedmiot do nowej listy
            except requests.exceptions.RequestException as e:
                print(f"Nie udało się pobrać szczegółów produktu o ID {product_id}: {e}")
                item['product_details'] = None  # Jeśli nie udało się pobrać danych produktu
                updated_cart_items.append(item)  # Dodajemy przedmiot z brakiem szczegółów

        cart_items = updated_cart_items  # Zastępujemy oryginalną listę nową
        print("Cart items po aktualizacji:", cart_items)

    except requests.exceptions.RequestException as e:
        flash("Nie udało się pobrać zawartości koszyka.", 'danger')
        print(f"Błąd żądania do serwisu koszyka: {e}")
        cart_items = []

    # Renderowanie szablonu z danymi koszyka
    return render_template('cart.html', cart_items=cart_items, user_id=user_id)

# Dodawanie produktu do koszyka
@app.route('/cart/add/<int:product_id>', methods=['POST'])
@login_required
def add_to_cart(product_id):
    try:
        headers = add_auth_headers()
        response = requests.post(f"{CART_SERVICE_URL}/add", json={'product_id': product_id}, headers=headers)
        response.raise_for_status()
        flash("Produkt dodany do koszyka.", 'success')
    except requests.exceptions.RequestException:
        flash("Nie udało się dodać produktu do koszyka.", 'danger')

    return redirect(url_for('show_products'))

# Usuwanie produktu z koszyka
@app.route('/cart/remove/<int:product_id>', methods=['POST'])
@login_required
def remove_from_cart(product_id):
    try:
        headers = add_auth_headers()  # Nagłówki autoryzacyjne
        # Wysłanie zapytania do serwisu koszyka w celu usunięcia produktu
        response = requests.post(f"{CART_SERVICE_URL}/remove", json={'product_id': product_id}, headers=headers)
        response.raise_for_status()  # Jeśli odpowiedź jest błędna, zostanie zgłoszony wyjątek
        flash("Produkt usunięty z koszyka.", 'success')
    except requests.exceptions.RequestException:
        flash("Nie udało się usunąć produktu z koszyka.", 'danger')

    return redirect(url_for('view_cart'))  # Po usunięciu produktu, przekierowanie do koszyka

# Aktualizacja ilości produktu w koszyku
@app.route('/cart/update/<int:item_id>', methods=['POST'])
@login_required
def update_cart(item_id):
    quantity = request.form.get('quantity', type=int)
    try:
        headers = add_auth_headers()
        response = requests.put(f"{CART_SERVICE_URL}/update/{item_id}", json={'quantity': quantity}, headers=headers)
        response.raise_for_status()
        flash("Koszyk zaktualizowany.", 'success')
    except requests.exceptions.RequestException:
        flash("Nie udało się zaktualizować koszyka.", 'danger')
    
    return redirect(url_for('view_cart'))

# Składanie zamówienia
@app.route('/checkout', methods=['POST'])
@login_required
def checkout():
    try:
        headers = add_auth_headers()
        response = requests.post(ORDER_SERVICE_URL, headers=headers)
        response.raise_for_status()
        flash("Zamówienie zostało złożone pomyślnie.", 'success')
    except requests.exceptions.RequestException:
        flash("Nie udało się złożyć zamówienia.", 'danger')
    
    return redirect(url_for('view_cart'))

# Wyświetlanie historii zamówień
@app.route('/orders')
@login_required
def view_orders():
    try:
        headers = add_auth_headers()
        response = requests.get(ORDER_SERVICE_URL, headers=headers)
        response.raise_for_status()
        orders = response.json()
    except requests.exceptions.RequestException:
        flash("Nie udało się pobrać historii zamówień.", 'danger')
        orders = []
    
    return render_template('orders.html', orders=orders)

if __name__ == '__main__':
    app.run(debug=True)
