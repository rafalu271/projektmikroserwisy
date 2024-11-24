Dostępne mikrousługi:
- Główna aplikacja - działa na porcie 5000
- Serwis rejestracji użutkowników - port 5001
- Serwis katalogu produktów - port 5002
- Serwis zarządzania zamówieniami - port 5003 (jeszcze nie ma)
- Serwis powiadomień - port 5004 (jeszcze nie ma)

Instralacja potrzebnych pakietów:

pip install -r requirements.txt

start aplikacji front-end:
- przejść do katalogu main i wykonać:
    python app.py

start aplikacji rejestracji userów:
- przejść do katalogu services\registration_service i wykonać:
    python .\registration_service.py

start aplikacji katalogów produktów:
- przejść do katalogu services\product_service i wykonać:
    python .\product_service.py

start aplikacji zamówień:
- przejść do katalogu services\product_service i wykonać:
    python .\orders_service.py

Aplikacja ma już przygotowane pliki docker-compose i Dockerfile dla gotowych aplikacji. Niestety nie ma jeszcze w pełni działającej konfiguracji Eureka.
