from datetime import datetime
from app.extensions import db


class Category(db.Model):
    __tablename__ = "categories"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False, unique=True)
    description = db.Column(db.Text, nullable=True)
    items = db.relationship("Item", backref="category", lazy="dynamic")

    def __repr__(self):
        return f"<Category {self.name}>"


class Item(db.Model):
    __tablename__ = "items"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(256), nullable=False)
    article = db.Column(db.String(64), nullable=True, unique=True)
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=True)
    unit = db.Column(db.String(32), nullable=False, default="шт")
    quantity = db.Column(db.Float, nullable=False, default=0.0)
    min_quantity = db.Column(db.Float, nullable=False, default=0.0)
    location = db.Column(db.String(128), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    order_items = db.relationship("OrderItem", backref="item", lazy="dynamic")

    @property
    def is_low_stock(self) -> bool:
        return self.quantity <= self.min_quantity

    def __repr__(self):
        return f"<Item {self.name} ({self.quantity} {self.unit})>"