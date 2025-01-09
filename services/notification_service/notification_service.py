from flask import Flask, request, jsonify
import consul
import os

app = Flask(__name__)


# Rejestracja usługi powiadomień w Consul
def register_service_with_consul():
    consul_client = consul.Consul(host=os.getenv('CONSUL_HOST', 'consul-server'), port=int(os.getenv('CONSUL_PORT', 8500)))
    
    service_name = "notification_service"
    service_id = f"{service_name}-{os.getenv('HOSTNAME', 'local')}"
    service_port = int(os.getenv('SERVICE_PORT', 5005))

    # Wyrejestrowanie, jeśli istnieje
    consul_client.agent.service.deregister(service_id)

    # Rejestracja usługi
    consul_client.agent.service.register(
        name=service_name,
        service_id=service_id,
        address=os.getenv('SERVICE_HOST', 'notification_service'),
        port=service_port,
        tags=[
            "traefik.enable=true",
            f"traefik.http.routers.{service_name}.rule=Host(`notification_service`) && PathPrefix(`/notifications`)",
            "traefik.http.services.notification_service.loadbalancer.server.scheme=http",
            f"traefik.http.services.notification_service.loadbalancer.server.port={service_port}",
            "flask"
        ]
    )
    print(f"Zarejestrowano usługę {service_name} w Consul")


@app.route('/notifications', methods=['POST'])
def send_notification():
    data = request.get_json()
    notification_type = data.get('type', 'generic')  # email, sms, etc.
    message = data.get('message', 'Brak treści powiadomienia')

    # Symulacja wysyłania powiadomienia
    print(f"[{notification_type.upper()}] {message}")

    return jsonify({'message': 'Powiadomienie zostało wysłane'}), 200

if __name__ == '__main__':
    # Rejestracja w Consul
    register_service_with_consul()

    app.run(debug=True, host='0.0.0.0', port=5005)
