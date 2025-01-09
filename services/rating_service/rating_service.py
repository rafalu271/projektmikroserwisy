from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import consul
import os

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///ratings.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


# Rejestracja usługi ocen w Consul
def register_service_with_consul():
    consul_client = consul.Consul(host=os.getenv('CONSUL_HOST', 'consul-server'), port=int(os.getenv('CONSUL_PORT', 8500)))
    
    service_name = "rating_service"
    service_id = f"{service_name}-{os.getenv('HOSTNAME', 'local')}"
    service_port = int(os.getenv('SERVICE_PORT', 5004))

    # Wyrejestrowanie, jeśli istnieje
    consul_client.agent.service.deregister(service_id)

    # Rejestracja usługi
    consul_client.agent.service.register(
        name=service_name,
        service_id=service_id,
        address=os.getenv('SERVICE_HOST', 'rating_service'),
        port=service_port,
        tags=[
            "traefik.enable=true",
            f"traefik.http.routers.{service_name}.rule=Host(`rating_service`) && PathPrefix(`/ratings`)",
            "traefik.http.services.rating_service.loadbalancer.server.scheme=http",
            f"traefik.http.services.rating_service.loadbalancer.server.port={service_port}",
            "flask"
        ]
    )
    print(f"Zarejestrowano usługę {service_name} w Consul")


class Rating(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, nullable=False)
    user_id = db.Column(db.Integer, nullable=False)
    score = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


@app.route('/ratings', methods=['POST'])
def add_rating():
    data = request.get_json()
    product_id = data.get('product_id')
    user_id = data.get('user_id')
    score = data.get('score')
    comment = data.get('comment', '')


    # Walidacja danych wejściowych
    if not user_id:
        return jsonify({'message': 'Brak ID użytkownika.'}), 400
    if not product_id:
        return jsonify({'message': 'Brak ID produktu.'}), 400
    if not (1 <= score <= 5):
        return jsonify({'message': 'Ocena musi być w zakresie od 1 do 5.'}), 400

    rating = Rating(product_id=product_id, user_id=user_id, score=score, comment=comment)
    db.session.add(rating)
    db.session.commit()
    return jsonify({'message': 'Dodano ocenę!'}), 201

@app.route('/ratings/<int:product_id>', methods=['GET'])
def get_ratings(product_id):
    ratings = Rating.query.filter_by(product_id=product_id).all()
    average_score = db.session.query(db.func.avg(Rating.score)).filter_by(product_id=product_id).scalar()
    return jsonify({
        'average_score': round(average_score, 2) if average_score else 0,
        'ratings': [{'user_id': r.user_id, 'score': r.score, 'comment': r.comment, 'created_at': r.created_at.isoformat()} for r in ratings]
    })

@app.route('/ratings/user/<int:user_id>', methods=['GET'])
def get_user_ratings(user_id):
    ratings = Rating.query.filter_by(user_id=user_id).all()
    return jsonify([{'product_id': r.product_id, 'score': r.score, 'comment': r.comment, 'created_at': r.created_at.isoformat()} for r in ratings])


if __name__ == '__main__':
    # Rejestracja w Consul
    register_service_with_consul()

    with app.app_context():
        db.create_all()
    app.run(debug=True, host='0.0.0.0', port=5004)
