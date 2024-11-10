# notification_service.py
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/notify', methods=['POST'])
def send_notification():
    notification_data = request.json
    # Logika wysyłania notyfikacji
    return jsonify({"status": "success", "message": "Notification sent successfully"})

if __name__ == "__main__":
    app.run(port=5003)
