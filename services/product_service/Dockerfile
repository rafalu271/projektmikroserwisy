# Używamy obrazu bazowego z Pythonem
FROM python:3.9-slim

# Ustawiamy katalog roboczy
WORKDIR /app

# Kopiujemy pliki aplikacji do kontenera
COPY . /app

# Instalujemy wymagane zależności
RUN pip install --no-cache-dir -r requirements.txt

# Eksponujemy port używany przez aplikację Flask
EXPOSE 5002

# Domyślna komenda uruchamiająca aplikację
CMD ["python", "product_service.py"]
