from flask import Flask, render_template, request, redirect, url_for, flash, session
import requests
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, DecimalField, IntegerField
from wtforms.validators import DataRequired, Length, EqualTo, NumberRange
from functools import wraps
import jwt
from dotenv import load_dotenv
import os
import consul
import time
import json
# from flask_consulate import Consul, ConsulManager


# Załadowanie zmiennych z pliku .env
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')  # Klucz do podpisywania sesji i tokenów

def register_service_with_consul():
    consul_client = consul.Consul(host=os.getenv('CONSUL_HOST', 'consul-server'), port=int(os.getenv('CONSUL_PORT', 8500)))
    
    service_id = "main_app_id"  # Unikalny identyfikator dla Twojej usługi

    # Sprawdź, czy usługa już istnieje i ją wyrejestruj przed ponownym rejestrowaniem
    consul_client.agent.service.deregister(service_id)
        
    # Rejestracja usługi
    service_name = "main_app"
    service_id = f"{service_name}-{os.getenv('HOSTNAME', 'local')}"
    service_port = int(os.getenv('SERVICE_PORT', 5000))

    consul_client.agent.service.register(
        name=service_name,
        service_id=service_id,
        address=os.getenv('SERVICE_HOST', 'main_app'),  # Użyj nazwy Dockera lub domyślnej
        port=service_port,
        tags=[
            "traefik.enable=true",
            f"traefik.http.routers.{service_name}.rule=Host(`main.local`)",
            f"traefik.http.services.{service_name}.loadbalancer.server.scheme=http",
            f"traefik.http.services.{service_name}.loadbalancer.server.port={service_port}",
            "flask"
        ]
    )
    print(f"Zarejestrowano usługę {service_name} w Consul")


def get_service_url(service_name):
    """Pobierz URL usługi z Consul"""
    try:
        consul_client = consul.Consul(host=os.getenv('CONSUL_HOST', 'consul-server'), port=int(os.getenv('CONSUL_PORT', 8500)))
        services = consul_client.agent.services()

        # Znajdź usługę w Consul
        service = next((s for s in services.values() if s['Service'] == service_name), None)
        if service:
            host = service.get('Address', '127.0.0.1')
            port = service.get('Port', 5000)
            return f"http://{host}:{port}"
        else:
            raise ValueError(f"Usługa {service_name} nie została znaleziona w Consul.")
    except Exception as e:
        print(f"Błąd podczas pobierania URL usługi {service_name}: {e}")
        return None


# def get_service_urls():
#     """Pobierz URL-e dla wszystkich wymaganych usług"""
#     return {
#         'REGISTER_SERVICE_URL': f"{get_service_url('registration_service')}/api/register",
#         'LOGIN_SERVICE_URL': f"{get_service_url('registration_service')}/api/login",
#         'PRODUCT_SERVICE_URL': get_service_url('product_service'),
#         'CART_SERVICE_URL': f"{get_service_url('orders_service')}/api/cart",
#         'ORDER_SERVICE_URL': f"{get_service_url('orders_service')}/api/orders",
#         'CHECKOUT_SERVICE_URL': f"{get_service_url('orders_service')}/api/orders/checkout",
#         'RATING_SERVICE_URL': f"{get_service_url('rating_service')}/ratings",
#         'NOTIFICATION_SERVICE_URL': f"{get_service_url('notification_service')}",
#     }

def get_service_urls():
    base_url = "http://traefik"
    return {
        'REGISTER_SERVICE_URL': f"{base_url}/api/register",
        'LOGIN_SERVICE_URL': f"{base_url}/api/login",
        'PRODUCT_SERVICE_URL': f"{base_url}",
        'CART_SERVICE_URL': f"{base_url}/api/cart",
        'ORDER_SERVICE_URL': f"{base_url}/api/orders",
        'CHECKOUT_SERVICE_URL': f"{base_url}/api/orders/checkout",
        'RATING_SERVICE_URL': f"{base_url}/ratings",
        # 'NOTIFICATION_SERVICE_URL': f"{base_url}/notifications",
    }


def get_service_url_from_config(service_name):
    """Pobierz URL z konfiguracji aplikacji"""
    urls = app.config.get('SERVICE_URLS', {})
    url = urls.get(service_name, None)  # Domyślnie None, jeśli brak klucza
    if url:
        print(f"Adres URL z konfiguracji dla '{service_name}': {url}")
    else:
        print(f"Nie znaleziono URL dla '{service_name}' w konfiguracji.")
    return url

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
    # def add_auth_headers(headers=None):
    #     if headers is None:
    #         headers = {}
    #     token = session.get('token')
    #     if token:
    #         headers['Authorization'] = f"Bearer {token}"
    #     return headers

def add_auth_headers(headers=None):
    if headers is None:
        headers = {}

    # Pobierz token z sesji
    token = session.get('token')

    # Jeśli token nie istnieje, ustaw domyślny placeholderowy token
    if not token:
        token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjo0LCJleHAiOjE3MzY1OTQ3NzB9.xkmS2KHJUjm39d4CL4ymnRokFy7Lro8CGd5srHwFxq4"

    # Dodaj nagłówek Authorization z tokenem
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
            register_service_url = get_service_url_from_config('REGISTER_SERVICE_URL')
            if not register_service_url:
                flash('Nie można znaleźć adresu URL dla usługi rejestracji.', 'danger')
                return render_template('register.html', form=form)
        
            response = requests.post(register_service_url, json=registration_data)
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
            login_service_url = get_service_url_from_config('LOGIN_SERVICE_URL')
            if not login_service_url:
                flash('Nie można znaleźć adresu URL dla usługi rejestracji.', 'danger')
                return render_template('login.html', form=form)

            response = requests.post(login_service_url, json={'username': username, 'password': password})
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
        # Pobranie dynamicznego URL-a dla usługi "product_service"
        product_service_url = get_service_url_from_config('PRODUCT_SERVICE_URL')
        if not product_service_url:
            raise ValueError("Nie znaleziono adresu URL dla 'PRODUCT_SERVICE_URL' w konfiguracji.")

        # Wysyłamy żądanie do usługi katalogu produktów
        api_endpoint = f"{product_service_url}/products"
        response = requests.get(api_endpoint)
        response.raise_for_status()
        products = response.json()
    except requests.exceptions.RequestException as e:
        # Logujemy błąd w przypadku problemów z żądaniem
        app.logger.error(f"Nie udało się pobrać listy produktów: {str(e)}")
        flash("Nie udało się pobrać listy produktów.", 'danger')
        products = []
    except ValueError as e:
        # Obsługa błędów związanych z brakiem konfiguracji
        app.logger.error(f"Błąd konfiguracji: {str(e)}")
        flash("Błąd konfiguracji: Nie można znaleźć adresu URL usługi produktów.", 'danger')
        products = []
    
    # Renderujemy stronę z listą produktów
    return render_template('products.html', products=products)

@app.route('/products/<int:product_id>', methods=['GET'])
def show_product(product_id):
    try:
        # Pobranie szczegółów produktu z serwisu produktów
        product_service_url = get_service_url_from_config('PRODUCT_SERVICE_URL')
        if not product_service_url:
            flash('Nie można znaleźć adresu URL dla usługi rejestracji.', 'danger')
            return render_template('product_detail.html', product=None)

        # Upewniamy się, że końcowy URL jest poprawny
        endpoint = f"{product_service_url}/{product_id}" if product_service_url.endswith('/products') else f"{product_service_url}/products/{product_id}"
        app.logger.info(f"Zapytanie do URL: {endpoint}")

        # Wysłanie zapytania do serwisu produktów w celu pobrania szczegółów produktu
        response = requests.get(endpoint)
        response.raise_for_status()  # Sprawdzamy, czy zapytanie się powiodło
        product = response.json()  # Otrzymujemy dane produktu w formacie JSON

        # Pobranie średniej oceny z serwisu ocen
        rating_service_url = get_service_url_from_config('RATING_SERVICE_URL')
        if rating_service_url:
            rating_response = requests.get(f"{rating_service_url}/{product_id}")
            if rating_response.status_code == 200:
                product['average_rating'] = rating_response.json().get('average_score', 'Brak ocen')
            else:
                product['average_rating'] = 'Brak ocen'

    except requests.exceptions.RequestException as e:
        app.logger.error(f"Błąd pobierania szczegółów produktu {product_id}: {e}")
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
            product_service_url = get_service_url_from_config('PRODUCT_SERVICE_URL')
            if not product_service_url:
                flash('Nie można znaleźć adresu URL dla usługi rejestracji.', 'danger')
                return render_template('product_form.html', form=form, product=None)

            response = requests.post(f"{product_service_url}/products", json=new_product)
            response.raise_for_status()
            flash('Produkt został dodany!', 'success')
            return redirect(url_for('show_products'))
        except requests.exceptions.RequestException:
            flash("Nie udało się dodać produktu.", 'danger')
    
    return render_template('product_form.html', form=form, product=None)

@app.route('/products/edit/<int:product_id>', methods=['GET', 'POST', 'PUT'])
def edit_product(product_id):
    form = ProductForm()  # Tworzymy instancję formularza
    product = None  # Domyślnie brak danych produktu

    # Obsługa formularza POST lub PUT (aktualizacja produktu)
    if form.validate_on_submit():
        updated_product = {
            'name': form.name.data,
            'description': form.description.data,
            'price': float(form.price.data),
            'quantity': int(form.quantity.data)
        }
        try:
            product_service_url = get_service_url_from_config('PRODUCT_SERVICE_URL')
            if not product_service_url:
                raise ValueError("Nie znaleziono adresu URL dla usługi produktów.")

            response = requests.put(f"{product_service_url}/products/{product_id}", json=updated_product)
            response.raise_for_status()
            flash('Produkt został zaktualizowany!', 'success')
            return redirect(url_for('show_products'))
        except requests.exceptions.RequestException as e:
            app.logger.error(f"Błąd aktualizacji produktu: {e}")
            flash("Nie udało się zaktualizować produktu.", 'danger')
        except ValueError as e:
            app.logger.error(f"Błąd konfiguracji: {e}")
            flash(str(e), 'danger')

    # Obsługa GET (pobranie szczegółów produktu)
    else:
        try:
            product_service_url = get_service_url_from_config('PRODUCT_SERVICE_URL')
            if not product_service_url:
                raise ValueError("Nie znaleziono adresu URL dla usługi produktów.")

            response = requests.get(f"{product_service_url}/products/{product_id}")
            response.raise_for_status()
            product = response.json()

            # Ustawienie danych w formularzu
            form.name.data = product.get('name')
            form.description.data = product.get('description')
            form.price.data = product.get('price')
            form.quantity.data = product.get('quantity')
        except requests.exceptions.RequestException as e:
            app.logger.error(f"Błąd pobierania szczegółów produktu: {e}")
            flash("Nie udało się pobrać szczegółów produktu.", 'danger')
            return redirect(url_for('show_products'))
        except ValueError as e:
            app.logger.error(f"Błąd konfiguracji: {e}")
            flash(str(e), 'danger')
            return redirect(url_for('show_products'))

    # Renderowanie formularza
    return render_template('product_form.html', form=form, product=product)

@app.route('/products/delete/<int:product_id>', methods=['POST'])
def delete_product(product_id):
    try:
        product_service_url = get_service_url_from_config('PRODUCT_SERVICE_URL')
        if not product_service_url:
            flash('Nie można znaleźć adresu URL dla usługi rejestracji.', 'danger')
            return redirect(url_for('show_products'))

        response = requests.delete(f"{product_service_url}/products/{product_id}")
        response.raise_for_status()
        flash('Produkt został usunięty!', 'success')
    except requests.exceptions.RequestException:
        flash("Nie udało się usunąć produktu.", 'danger')
    
    return redirect(url_for('show_products'))


#System ocen dla produktów 
@app.route('/products/<int:product_id>/rating', methods=['POST'])
# @login_required
def add_rating(product_id):
    # try:

        token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjo0LCJleHAiOjE3MzY1MjE2MjB9.bom1NRTc9SgEP9JfsRDgGY0XchLeUl_nU9WwNN8ELMU:"
        username = "test2137"
        user_id = 4

        # # Pobranie tokenu z sesji
        # token = session.get('token')
        # user_id = None
        # username = None

        # Pobranie URL serwisu ocen z konfiguracji
        rating_service_url = get_service_url_from_config('RATING_SERVICE_URL')
        if not rating_service_url:
            flash('Nie można znaleźć URL dla systemu ocen.', 'danger')
            return redirect(url_for('show_product', product_id=product_id))

        # # Dekodowanie tokenu JWT
        # if token:
        #     try:
        #         decoded_token = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
        #         username = decoded_token.get('username')  # Pobieranie username z tokenu
        #         user_id = decoded_token.get('user_id')
        #     except jwt.ExpiredSignatureError:
        #         flash("Token wygasł, proszę się zalogować ponownie.", 'danger')
        #         return redirect(url_for('login'))
        #     except jwt.InvalidTokenError:
        #         flash("Nieprawidłowy token, proszę spróbować ponownie.", 'danger')
        #         return redirect(url_for('login'))
        # else:
        #     flash("Brak tokenu autoryzacyjnego, proszę się zalogować.", 'danger')
        #     return redirect(url_for('login'))

        # Pobranie danych oceny i komentarza z formularza
        score = int(request.form.get('score'))
        comment = request.form.get('comment', '').strip()

        # Walidacja oceny
        if not (1 <= score <= 5):
            flash('Ocena musi być w zakresie od 1 do 5.', 'danger')
            return redirect(url_for('show_product', product_id=product_id))

        # Przygotowanie danych do wysłania
        data = {
            'product_id': product_id,
            'user_id': user_id,
            'score': score,
            'comment': comment
        }

        print("Data sent to rating service:", json.dumps(data, indent=4))  # Debugowanie danych

        # Wysłanie danych do mikroserwisu ocen
        headers = {'Authorization': f'Bearer {token}'}  # Dodanie tokena do nagłówków
        response = requests.post(f"{rating_service_url}", json=data, headers=headers)
        
        # Logowanie pełnej odpowiedzi przed próbą dekodowania JSON
        print("Response status code:", response.status_code)
        print("Response text:", response.text)  # Debugowanie tekstu odpowiedzi

        # Obsługa odpowiedzi
        if response.status_code == 201:
            flash('Dodano ocenę!', 'success')
        else:
            # Bezpieczne odczytanie JSON lub logowanie błędu
            try:
                error_message = response.json().get("message", "Nieznany błąd")
            except ValueError:  # Jeśli odpowiedź nie jest JSON
                error_message = "Nieprawidłowa odpowiedź z serwisu ocen."
            flash(f'Nie udało się dodać oceny: {error_message}', 'danger')
    #except Exception as e:
    #    app.logger.error(f"Błąd podczas dodawania oceny dla produktu {product_id}: {e}")
    #   flash('Wystąpił problem podczas dodawania oceny.', 'danger')

        return redirect(url_for('show_product', product_id=product_id))


@app.route('/cart', methods=['GET', 'POST'])
def view_cart():
    try:
        # Pobranie tokenu z sesji
        token = session.get('token')
        user_id = None
        username = None

        if token:
            try:
                # Dekodowanie tokenu, jeśli jest dostępny
                decoded_token = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
                username = decoded_token.get('username')  # Pobieranie username z tokenu
                user_id = decoded_token.get('user_id')
            except jwt.ExpiredSignatureError:
                flash("Token wygasł, proszę się zalogować ponownie.", 'danger')
                return redirect(url_for('login'))
            except jwt.InvalidTokenError:
                flash("Nieprawidłowy token, proszę się zalogować ponownie.", 'danger')
                return redirect(url_for('login'))

        # Jeśli tokenu brak lub `user_id` nie jest dostępne, pobierz z JSON w żądaniu
        if not user_id:
            data = request.get_json()
            if data and 'user_id' in data:
                user_id = data.get('user_id')

        if not user_id:
            flash("Nie można pobrać historii zamówień. Brak ID użytkownika.", 'danger')
            return redirect(url_for('show_products'))

        cart_service_url = get_service_url_from_config('CART_SERVICE_URL')
        if not cart_service_url:
            flash('Nie można znaleźć adresu URL dla usługi koszyka.', 'danger')
            return redirect(url_for('show_products'))

        # Pobranie danych o koszyku
        data = {'user_id': user_id}  # Przesyłamy user_id w JSON
        response = requests.get(cart_service_url, json=data)
        response.raise_for_status()

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
                product_service_url = get_service_url_from_config('PRODUCT_SERVICE_URL')
                if not product_service_url:
                    flash('Nie można znaleźć adresu URL dla usługi produktów.', 'danger')
                    return redirect(url_for('show_products'))

                # Wykonaj zapytanie do serwisu produktów, aby pobrać szczegóły produktu
                product_response = requests.get(f"{product_service_url}/products/{product_id}")
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
def add_to_cart(product_id):
    try:
        cart_service_url = get_service_url_from_config('CART_SERVICE_URL')
        if not cart_service_url:
            flash('Nie można znaleźć adresu URL dla usługi koszyka.', 'danger')
            return redirect(url_for('show_products'))

        # Pobranie tokenu z sesji
        token = session.get('token')
        user_id = None
        username = None

        if token:
            try:
                # Dekodowanie tokenu, jeśli jest dostępny
                decoded_token = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
                username = decoded_token.get('username')  # Pobieranie username z tokenu
                user_id = decoded_token.get('user_id')
            except jwt.ExpiredSignatureError:
                flash("Token wygasł, proszę się zalogować ponownie.", 'danger')
                return redirect(url_for('login'))
            except jwt.InvalidTokenError:
                flash("Nieprawidłowy token, proszę się zalogować ponownie.", 'danger')
                return redirect(url_for('login'))

        # Jeśli tokenu brak lub `user_id` nie jest dostępne, pobierz z JSON w żądaniu
        if not user_id:
            data = request.get_json()
            if data and 'user_id' in data:
                user_id = data.get('user_id')

        if not user_id:
            flash("Nie można pobrać historii zamówień. Brak ID użytkownika.", 'danger')
            return redirect(url_for('show_products'))

        # Przygotowanie danych do wysłania w JSON
        data = {
            'user_id': user_id,
            'product_id': product_id,
            'quantity': 1  # Domyślna ilość dodawana do koszyka
        }

        # Wysłanie żądania POST do mikroserwisu koszyka
        response = requests.post(f"{cart_service_url}/add", json=data)
        response.raise_for_status()

        flash("Produkt dodany do koszyka.", 'success')
    except requests.exceptions.RequestException as e:
        app.logger.error(f"Błąd dodawania produktu do koszyka: {e}")
        flash("Nie udało się dodać produktu do koszyka.", 'danger')

    return redirect(url_for('show_products'))


# Usuwanie produktu z koszyka
@app.route('/cart/remove/<int:product_id>', methods=['POST'])
def remove_from_cart(product_id):
    try:
        cart_service_url = get_service_url_from_config('CART_SERVICE_URL')
        if not cart_service_url:
            flash('Nie można znaleźć adresu URL dla usługi koszyka.', 'danger')
            return redirect(url_for('show_products'))

        # Pobranie tokenu z sesji
        token = session.get('token')
        user_id = None
        username = None

        if token:
            try:
                # Dekodowanie tokenu, jeśli jest dostępny
                decoded_token = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
                username = decoded_token.get('username')  # Pobieranie username z tokenu
                user_id = decoded_token.get('user_id')
            except jwt.ExpiredSignatureError:
                flash("Token wygasł, proszę się zalogować ponownie.", 'danger')
                return redirect(url_for('login'))
            except jwt.InvalidTokenError:
                flash("Nieprawidłowy token, proszę się zalogować ponownie.", 'danger')
                return redirect(url_for('login'))

        # Jeśli tokenu brak lub `user_id` nie jest dostępne, pobierz z JSON w żądaniu
        if not user_id:
            data = request.get_json()
            if data and 'user_id' in data:
                user_id = data.get('user_id')

        if not user_id:
            flash("Nie można pobrać historii zamówień. Brak ID użytkownika.", 'danger')
            return redirect(url_for('show_products'))

        # Przygotowanie danych do wysłania w JSON
        data = {
            'user_id': user_id,
            'product_id': product_id
        }

        # Wysłanie żądania POST do mikroserwisu koszyka
        response = requests.post(f"{cart_service_url}/remove", json=data)
        response.raise_for_status()

        flash("Produkt usunięty z koszyka.", 'success')
    except requests.exceptions.RequestException as e:
        app.logger.error(f"Błąd usuwania produktu z koszyka: {e}")
        flash("Nie udało się usunąć produktu z koszyka.", 'danger')

    return redirect(url_for('view_cart'))

# Aktualizacja ilości produktu w koszyku
@app.route('/cart/update/<int:item_id>', methods=['POST'])
def update_cart(item_id):
    quantity = request.form.get('quantity', type=int)
    try:
        cart_service_url = get_service_url_from_config('CART_SERVICE_URL')
        if not cart_service_url:
            flash('Nie można znaleźć adresu URL dla usługi koszyka.', 'danger')
            return redirect(url_for('show_products'))

        # Pobranie tokenu z sesji
        token = session.get('token')
        user_id = None
        username = None

        if token:
            try:
                # Dekodowanie tokenu, jeśli jest dostępny
                decoded_token = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
                username = decoded_token.get('username')  # Pobieranie username z tokenu
                user_id = decoded_token.get('user_id')
            except jwt.ExpiredSignatureError:
                flash("Token wygasł, proszę się zalogować ponownie.", 'danger')
                return redirect(url_for('login'))
            except jwt.InvalidTokenError:
                flash("Nieprawidłowy token, proszę się zalogować ponownie.", 'danger')
                return redirect(url_for('login'))

        # Jeśli tokenu brak lub `user_id` nie jest dostępne, pobierz z JSON w żądaniu
        if not user_id:
            data = request.get_json()
            if data and 'user_id' in data:
                user_id = data.get('user_id')

        if not user_id:
            flash("Nie można pobrać historii zamówień. Brak ID użytkownika.", 'danger')
            return redirect(url_for('show_products'))

        # Przygotowanie danych do wysłania w JSON
        data = {
            'user_id': user_id,
            'item_id': item_id,
            'quantity': quantity
        }

        # Wysłanie żądania PUT do mikroserwisu koszyka
        response = requests.put(f"{cart_service_url}/update", json=data)
        response.raise_for_status()

        flash("Koszyk zaktualizowany.", 'success')
    except requests.exceptions.RequestException as e:
        app.logger.error(f"Błąd aktualizacji koszyka: {e}")
        flash("Nie udało się zaktualizować koszyka.", 'danger')

    return redirect(url_for('view_cart'))

# Składanie zamówienia
@app.route('/checkout', methods=['POST'])
def checkout():
    try:
        # Pobierz URL serwisu zamówień
        order_service_url = get_service_url_from_config('CHECKOUT_SERVICE_URL')
        if not order_service_url:
            flash('Nie można znaleźć adresu URL dla usługi zamówień.', 'danger')
            return redirect(url_for('view_cart'))

        # Pobranie tokenu z sesji
        token = session.get('token')
        user_id = None
        username = None

        if token:
            try:
                # Dekodowanie tokenu, jeśli jest dostępny
                decoded_token = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
                username = decoded_token.get('username')  # Pobieranie username z tokenu
                user_id = decoded_token.get('user_id')
            except jwt.ExpiredSignatureError:
                flash("Token wygasł, proszę się zalogować ponownie.", 'danger')
                return redirect(url_for('login'))
            except jwt.InvalidTokenError:
                flash("Nieprawidłowy token, proszę się zalogować ponownie.", 'danger')
                return redirect(url_for('login'))

        # Jeśli tokenu brak lub `user_id` nie jest dostępne, pobierz z JSON w żądaniu
        if not user_id:
            data = request.get_json()
            if data and 'user_id' in data:
                user_id = data.get('user_id')

        if not user_id:
            flash("Nie można pobrać historii zamówień. Brak ID użytkownika.", 'danger')
            return redirect(url_for('show_products'))

        # Przygotowanie danych do wysłania w JSON
        data = {'user_id': user_id}

        # Wysłanie żądania POST do mikroserwisu zamówień
        response = requests.post(order_service_url, json=data)
        response.raise_for_status()

        # Obsługa odpowiedzi
        flash("Zamówienie zostało złożone pomyślnie.", 'success')
    except requests.exceptions.RequestException as e:
        app.logger.error(f"Błąd składania zamówienia: {e}")
        flash("Nie udało się złożyć zamówienia.", 'danger')
    
    return redirect(url_for('view_cart'))

# Wyświetlanie historii zamówień
@app.route('/orders', methods=['GET', 'POST'])
def view_orders():
    try:
        # Pobranie URL dla usługi zamówień
        order_service_url = get_service_url_from_config('ORDER_SERVICE_URL')
        if not order_service_url:
            flash('Nie można znaleźć adresu URL dla usługi zamówień.', 'danger')
            return redirect(url_for('show_products'))

        # Pobranie tokenu z sesji
        token = session.get('token')
        user_id = None
        username = None

        if token:
            try:
                # Dekodowanie tokenu, jeśli jest dostępny
                decoded_token = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
                username = decoded_token.get('username')  # Pobieranie username z tokenu
                user_id = decoded_token.get('user_id')
            except jwt.ExpiredSignatureError:
                flash("Token wygasł, proszę się zalogować ponownie.", 'danger')
                return redirect(url_for('login'))
            except jwt.InvalidTokenError:
                flash("Nieprawidłowy token, proszę się zalogować ponownie.", 'danger')
                return redirect(url_for('login'))

        # Jeśli tokenu brak lub `user_id` nie jest dostępne, pobierz z JSON w żądaniu
        if not user_id:
            data = request.get_json()
            if data and 'user_id' in data:
                user_id = data.get('user_id')

        if not user_id:
            flash("Nie można pobrać historii zamówień. Brak ID użytkownika.", 'danger')
            return redirect(url_for('show_products'))

        # Przygotowanie danych do wysłania w JSON
        data = {'user_id': user_id}

        # Wysłanie żądania POST do mikroserwisu zamówień
        response = requests.post(order_service_url, json=data)
        response.raise_for_status()

        # Pobranie i przetworzenie odpowiedzi
        orders = response.json()

        # Upewnienie się, że `items` jest listą w każdym zamówieniu
        for order in orders:
            order['items'] = list(order.get('items', []))  # Konwersja na listę, jeśli to konieczne

    except requests.exceptions.RequestException as e:
        app.logger.error(f"Błąd pobierania historii zamówień: {e}")
        flash("Nie udało się pobrać historii zamówień.", 'danger')
        orders = []

    return render_template('orders.html', orders=orders)


if __name__ == '__main__':
    # Rejestracja usługi w Consul
    register_service_with_consul()

    # time.sleep(30)  # Czeka przez 2 sekundy
    # Załaduj URL-e usług do konfiguracji aplikacji
    app.config['SERVICE_URLS'] = get_service_urls()

    # Uruchom aplikację Flask
    app.run(debug=True, host='0.0.0.0', port=5000)