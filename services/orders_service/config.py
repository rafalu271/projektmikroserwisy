import os

class Config:
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'sqlite:///orders.db')  # Zmienna środowiskowa lub SQLite
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = os.getenv('SECRET_KEY', 'mysecretkey')

def load_service_urls():
    product_service_url = get_service_url('product_service')
    app.config['PRODUCT_SERVICE_URL'] = f"{product_service_url}/products"
