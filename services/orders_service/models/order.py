from db import db

class Order(db.Model):
    __tablename__ = 'orders'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    total_price = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(50), default='Oczekujące')
    # Zmiana nazwy relacji
    order_items = db.relationship('OrderItem', back_populates='order', lazy='joined', cascade="all, delete-orphan")

class OrderItem(db.Model):
    __tablename__ = 'order_items'
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    product_id = db.Column(db.Integer, nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)

    # Relacja do zamówienia
    order = db.relationship('Order', back_populates='order_items')

    def to_dict(self):
        return {
            'product_id': self.product_id,
            'quantity': self.quantity
        }
