from datetime import datetime
from app.extensions import db


class Order(db.Model):
    __tablename__ = "orders"

    STATUS_CHOICES = {
        "new": "Новый",
        "in_progress": "В работе",
        "issued": "Выдан",
        "cancelled": "Отменён",
    }

    id = db.Column(db.Integer, primary_key=True)
    number = db.Column(db.String(32), unique=True, nullable=False)
    object_name = db.Column(db.String(256), nullable=False)
    status = db.Column(db.String(32), nullable=False, default="new")
    notes = db.Column(db.Text, nullable=True)

    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    assigned_to_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    issued_at = db.Column(db.DateTime, nullable=True)

    items = db.relationship(
        "OrderItem", backref="order", lazy="select", cascade="all, delete-orphan"
    )

    @property
    def status_label(self) -> str:
        return self.STATUS_CHOICES.get(self.status, self.status)

    @property
    def total_items(self) -> int:
        return len(self.items)

    def __repr__(self):
        return f"<Order {self.number} [{self.status}]>"


class OrderItem(db.Model):
    __tablename__ = "order_items"

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey("items.id"), nullable=False)
    quantity = db.Column(db.Float, nullable=False)
    issued_quantity = db.Column(db.Float, nullable=True, default=0.0)
    notes = db.Column(db.String(256), nullable=True)