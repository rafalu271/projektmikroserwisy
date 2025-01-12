Projekt aplikacji opartej o mikrousługi.

Dostępne mikrousługi:
- Główna aplikacja front-end - port 5000
- Serwis rejestracji użytkowników - port 5001
- Serwis katalogu produktów - port 5002
- Serwis zarządzania zamówieniami - port 5003
- Serwis ocen produktów - port 5004
- Serwis powiadomień - port 5005

Uruchamianie aplikacji (Docker)

- Upewnij się, że masz zainstalowane środowisko Docker oraz Docker Compose.
- Pobierz repozytorium i rozpakuj je.
- Otwórz terminal w katalogu main repozytorium.
- Wykonaj polecenie:
    docker-compose up

Po tych krokach całe środowisko wraz z zależnościami powinno zostać uruchomione.

Dostęp
    Główna aplikacja jest dostępna pod adresem: http://localhost:5000/.

Aplikacja korzysta z technologii:
- Flask - główna logika aplikacji
- Consul - Service Discovery
- Traefik - API Gateway
- RabbitMQ - komunikacja między mikroserwisami (Inter-Service Communication)

Endpointy API
Poszczególne mikroserwisy można obsługiwać za pomocą aplikacji front-end lub bezpośrednio poprzez poniższe endpointy (osiągalne przez API Gateway):

Serwis rejestracji użytkowników (Registration)
    
    Rejestracja użytkownika: 
        POST http://localhost/api/register 

            Body: 
                {
                    "username": "{userName}", 
                    "password": "{userPassword}", 
                    "confirm_password": "{userPassword}" 
                }

    Logowanie użytkownika: 
        POST http://localhost/api/login

            Body: 
                { 
                    "username": "{userName}", 
                    "password": "{userPassword}"  
                } 

Serwis katalogu produktów (Product)

    Lista produktów: 
        GET http://localhost/products 
    
    Informacje o produkcie: 
        GET http://localhost/products/{productID} 
    
    Dodanie nowego produkt do listy produktów: 
        POST http://localhost/products 

            Body: 
                { 
                    "name": "{productName}", 
                    "description": "{productDescription}", 
                    "price": {productPrice}, 
                    "quantity": {productQuantity} 
                } 

    Zmiana danych produktu: 
        PUT http://localhost/products/{productID}

            Body: 
                { 
                    "name": "{productName}", 
                    "description": "{productDescription}", 
                    "price": {productPrice}, 
                    "quantity": {productQuantity} 
                } 

    Usunięcie produktu z listy produktów: 
        DELETE    http://localhost/products/{productID}

Serwis zamówień i koszyka (Orders) 
    
    Zawartość koszyka zakupowego: 
        GET http://localhost/api/cart

            Body:  
                {
                    "user_id": {userID} 
                } 

    Dodanie produktu do koszyka: 
        POST http://localhost/api/cart/add 

            Body: 
                { 
                    "product_id": {productID}, 
                    "user_id": {userID}, 
                    "quantity": {productQuantity} 
                }  

    Zmiana zawartości produktu w koszyku: 
        POST http://localhost/api/cart/update 

            Body: 
                { 
                    "user_id": {userID}, 
                    "product_id": {productID}, 
                    "quantity": {productQuantity} 
                } 

    Usunięcie produktu z koszyka: 
        POST  http://localhost/api/cart/remove

            Body: 
                { 
                    "user_id": {userID}, 
                    "product_id": {productID} 
                } 

    Złożenie zamówienia: 
        POST http://localhost/api/orders/checkout

            Body: 
                {
                    "user_id": {userID} 
                } 

    Historia zamówień: 
        POST http://localhost/api/orders

            Body: 
                {
                    "user_id": {userID} 
                } 

Serwis ocen produktów (Rating)
    
    Wystawienie oceny dla danego produktu: 
        POST http://localhost/ratings

            Body: 
                { 
                    "score": {productScore}, 
                    "comment": "{productComment}", 
                    "product_id": {productID}, 
                    "user_id": {userID} 
                } 

    Średnia ocen dla danego produktu: 
        GET http://localhost/ratings/{productID} 
    
    Lista ocen wystawionych przez danego użytkownika: 
        GET http://localhost/ratings/user/{userID}

Serwis powiadomień (Notifications)
    Ten serwis nie ma publicznych endpointów.
    Powiadomienia są wysyłane wewnętrznie między mikroserwisami za pomocą RabbitMQ.
