# Używamy obrazu bazowego Pythona
FROM python:3.12-slim

# Ustawiamy katalog roboczy
WORKDIR /app

# Kopiujemy plik requirements.txt
COPY requirements.txt .

# Instalujemy zależności
RUN pip install --no-cache-dir -r requirements.txt

# Kopiujemy całą aplikację do obrazu
COPY . .

# Ustawiamy zmienną środowiskową dla Flask
ENV FLASK_APP=app.py
ENV FLASK_RUN_HOST=0.0.0.0

# Otwieramy port aplikacji
EXPOSE 5000

# Uruchamiamy aplikację Flask
CMD ["python", "app.py"]
