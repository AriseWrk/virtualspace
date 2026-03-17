import os
from datetime import datetime, date
from app.extensions import db


class Vehicle(db.Model):
    """Транспортное средство."""
    __tablename__ = "vehicles"

    STATUS_CHOICES = {
        "available":   "Свободен",
        "on_route":    "В пути",
        "maintenance": "ТО / Ремонт",
        "inactive":    "Выведен из эксплуатации",
    }

    id              = db.Column(db.Integer, primary_key=True)
    name            = db.Column(db.String(128), nullable=False)      # Марка + модель
    plate           = db.Column(db.String(32),  nullable=False, unique=True)  # Госномер
    year            = db.Column(db.Integer,     nullable=True)
    color           = db.Column(db.String(32),  nullable=True)
    status          = db.Column(db.String(32),  nullable=False, default="available")

    mileage         = db.Column(db.Integer,     nullable=False, default=0)   # Пробег км

    # Ответственный водитель (из пользователей)
    driver_id       = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    # Документы
    sto_date        = db.Column(db.Date, nullable=True)          # Дата последнего ТО
    sto_next_date   = db.Column(db.Date, nullable=True)          # Дата следующего ТО
    insurance_date  = db.Column(db.Date, nullable=True)          # ОСАГО до
    inspection_date = db.Column(db.Date, nullable=True)          # Техосмотр до

    notes           = db.Column(db.Text, nullable=True)
    created_at      = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at      = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    driver  = db.relationship("User", foreign_keys=[driver_id])
    trips   = db.relationship("VehicleTrip",    backref="vehicle", lazy="dynamic",
                               cascade="all, delete-orphan",
                               order_by="VehicleTrip.date.desc()")
    requests = db.relationship("VehicleRequest", backref="vehicle", lazy="dynamic",
                                cascade="all, delete-orphan",
                                order_by="VehicleRequest.created_at.desc()")

    @property
    def status_label(self):
        return self.STATUS_CHOICES.get(self.status, self.status)

    @property
    def insurance_days_left(self):
        if self.insurance_date:
            return (self.insurance_date - date.today()).days
        return None

    @property
    def inspection_days_left(self):
        if self.inspection_date:
            return (self.inspection_date - date.today()).days
        return None

    @property
    def sto_days_left(self):
        if self.sto_next_date:
            return (self.sto_next_date - date.today()).days
        return None

    @property
    def has_warnings(self):
        for days in (self.insurance_days_left, self.inspection_days_left, self.sto_days_left):
            if days is not None and days <= 30:
                return True
        return False

    def __repr__(self):
        return f"<Vehicle {self.plate} {self.name}>"


class VehicleTrip(db.Model):
    """Поездка / рейс."""
    __tablename__ = "vehicle_trips"

    id              = db.Column(db.Integer, primary_key=True)
    vehicle_id      = db.Column(db.Integer, db.ForeignKey("vehicles.id"), nullable=False)
    driver_id       = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    date            = db.Column(db.Date, nullable=False, default=date.today)
    destination     = db.Column(db.String(256), nullable=False)   # Куда
    purpose         = db.Column(db.String(256), nullable=True)    # Цель
    passengers      = db.Column(db.String(256), nullable=True)    # С кем

    mileage_start   = db.Column(db.Integer, nullable=True)
    mileage_end     = db.Column(db.Integer, nullable=True)

    departed_at     = db.Column(db.DateTime, nullable=True)
    arrived_at      = db.Column(db.DateTime, nullable=True)

    notes           = db.Column(db.Text, nullable=True)
    created_at      = db.Column(db.DateTime, default=datetime.utcnow)

    driver = db.relationship("User", foreign_keys=[driver_id])

    @property
    def distance(self):
        if self.mileage_start and self.mileage_end:
            return self.mileage_end - self.mileage_start
        return None

    def __repr__(self):
        return f"<VehicleTrip vehicle={self.vehicle_id} {self.date}>"


class VehicleRequest(db.Model):
    """Заявка сотрудника на транспорт."""
    __tablename__ = "vehicle_requests"

    STATUS_CHOICES = {
        "new":       "Новая",
        "approved":  "Одобрена",
        "rejected":  "Отклонена",
        "done":      "Выполнена",
    }

    id          = db.Column(db.Integer, primary_key=True)
    vehicle_id  = db.Column(db.Integer, db.ForeignKey("vehicles.id"), nullable=True)

    requester_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    status       = db.Column(db.String(32), nullable=False, default="new")

    planned_date = db.Column(db.Date, nullable=False)
    destination  = db.Column(db.String(256), nullable=False)
    purpose      = db.Column(db.String(256), nullable=True)
    passengers   = db.Column(db.Integer, nullable=True, default=1)
    notes        = db.Column(db.Text, nullable=True)

    reviewed_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    review_note    = db.Column(db.String(256), nullable=True)
    created_at     = db.Column(db.DateTime, default=datetime.utcnow)

    requester   = db.relationship("User", foreign_keys=[requester_id])
    reviewed_by = db.relationship("User", foreign_keys=[reviewed_by_id])

    @property
    def status_label(self):
        return self.STATUS_CHOICES.get(self.status, self.status)

    def __repr__(self):
        return f"<VehicleRequest {self.id} [{self.status}]>"