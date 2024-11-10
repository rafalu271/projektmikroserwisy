# order_service.py
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/order', methods=['POST'])
def create_order():
    order_data = request.json
    # Logika tworzenia zamówienia
    return jsonify({"status": "success", "message": "Order created successfully"})

if __name__ == "__main__":
    app.run(port=5002)
