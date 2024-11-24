# Użyj oficjalnego obrazu Python jako bazowego
FROM python:3.12-slim

# Ustaw zmienną środowiskową do nieinteraktywnej instalacji
ENV PYTHONUNBUFFERED 1

# Stwórz katalog roboczy
WORKDIR /app

# Skopiuj wymagania do obrazu
COPY requirements.txt /app/requirements.txt

# Zainstaluj wymagane pakiety
RUN pip install --no-cache-dir -r /app/requirements.txt

# Skopiuj pozostałe pliki aplikacji
COPY . /app

# Ustaw zmienną PORT
ENV PORT=5003

# Eksponuj port aplikacji
EXPOSE 5003

# Uruchom aplikację
CMD ["python", "orders_service.py"]
