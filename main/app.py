# app.py
from flask import Flask, render_template, request, redirect, url_for, flash
import requests
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Length, EqualTo

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'

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
            # Żądanie do mikrousługi rejestracji (zakładając, że działa na porcie 5001)
            response = requests.post('http://localhost:5001/register', json=registration_data)
            if response.status_code == 201:
                flash('Registration successful! You can now log in.', 'success')
                return redirect(url_for('login'))
            else:
                flash(response.json().get('message', 'Registration failed'), 'danger')
        except requests.exceptions.ConnectionError:
            flash('Could not connect to the registration service.', 'danger')
    return render_template('register.html', form=form)

# Logowanie użytkownika
@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        # Tutaj można dodać logikę logowania, sprawdzając dane w bazie
        pass
    return render_template('login.html', form=form)

if __name__ == '__main__':
    app.run(debug=True)
