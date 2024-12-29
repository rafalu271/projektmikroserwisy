Dostępne mikrousługi:
- Główna aplikacja - działa na porcie 5000
- Serwis rejestracji użutkowników - port 5001
- Serwis katalogu produktów - port 5002
- Serwis zarządzania zamówieniami - port 5003
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

Obecnie można uruchomić pojedyncze serwisy aplikacji jednak nie będą w stanie się między sobą komunikować. Konfiguracja jest przygotowana pod środowisko dokerowe z wykorzystaniem Consula oraz Traefik.

Uruchamianie aplikacji - Docker:

- przed uruchomieniem należy przygotować środowisko docker z docker compose
- pobrać repozytorium i rozpakować
- otworzyć konsolę cmd w katalogu "main"
- wykonać polecenie "docker-compose up"

Po tych krokach całe środowisko wraz z zależnościami powinno zostać utworzone.

Uruchomiona aplkacja znajduje się pod adresem: http://localhost:5000/