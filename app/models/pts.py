from datetime import datetime
from app.extensions import db


class ObjectCategory(db.Model):
    __tablename__ = "object_categories"

    id          = db.Column(db.Integer, primary_key=True)
    name        = db.Column(db.String(128), nullable=False, unique=True)
    description = db.Column(db.String(512), nullable=True)
    color       = db.Column(db.String(16), nullable=False, default="#b98c50")
    order       = db.Column(db.Integer, default=0)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)
    created_by  = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    objects = db.relationship(
        "ServiceObject", backref="category",
        lazy="dynamic", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<ObjectCategory {self.name}>"


class ServiceObject(db.Model):
    __tablename__ = "service_objects"

    STATUS_CHOICES = {
        "active":         "На обслуживании",
        "warranty":       "На гарантии",
        "one_time":       "Разовый",
        "inactive":       "Снят с обслуживания",
        "inst_survey":    "Обследование",
        "inst_design":    "Проектирование",
        "inst_mounting":  "Монтаж",
        "inst_pnr":       "ПНР",
        "inst_done":      "Сдан",
        "inst_cancelled": "Отменён",
    }

    INSTALLATION_STAGES = {
        "inst_survey":    "Обследование",
        "inst_design":    "Проектирование",
        "inst_mounting":  "Монтаж",
        "inst_pnr":       "ПНР",
        "inst_done":      "Сдан",
        "inst_cancelled": "Отменён",
    }

    id              = db.Column(db.Integer, primary_key=True)
    name            = db.Column(db.String(256), nullable=False)
    address         = db.Column(db.String(512), nullable=True)
    category_id     = db.Column(db.Integer, db.ForeignKey("object_categories.id"), nullable=False)
    status          = db.Column(db.String(32), nullable=False, default="active")
    section         = db.Column(db.String(32), nullable=False, default="service")

    client_name     = db.Column(db.String(256), nullable=True)
    client_contact  = db.Column(db.String(256), nullable=True)
    client_phone    = db.Column(db.String(64), nullable=True)
    client_email    = db.Column(db.String(128), nullable=True)

    systems         = db.Column(db.String(512), nullable=True)

    engineer_id     = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    engineer        = db.relationship("User", foreign_keys=[engineer_id])

    commissioned_at    = db.Column(db.DateTime, nullable=True)
    next_to_date       = db.Column(db.DateTime, nullable=True)
    notes              = db.Column(db.Text, nullable=True)

    estimate_sum       = db.Column(db.Float, nullable=True)
    installation_stage = db.Column(db.String(32), nullable=True)
    handover_date      = db.Column(db.DateTime, nullable=True)
    contract_number    = db.Column(db.String(128), nullable=True)

    created_at      = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at      = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    service_records = db.relationship(
        "ServiceRecord", backref="object", lazy="select",
        cascade="all, delete-orphan",
        order_by="ServiceRecord.date.desc()"
    )
    passwords = db.relationship(
        "ObjectPassword", backref="object", lazy="select",
        cascade="all, delete-orphan"
    )
    files = db.relationship(
        "ObjectFile", backref="object", lazy="select",
        cascade="all, delete-orphan",
        order_by="ObjectFile.uploaded_at.desc()"
    )
    equipment = db.relationship(
        "ObjectEquipment", backref="object", lazy="select",
        cascade="all, delete-orphan"
    )

    @property
    def status_label(self):
        return self.STATUS_CHOICES.get(self.status, self.status)

    @property
    def last_service(self):
        return self.service_records[0] if self.service_records else None

    @property
    def last_to(self):
        for rec in self.service_records:
            if rec.record_type == "to":
                return rec
        return None

    def __repr__(self):
        return f"<ServiceObject {self.name}>"


class ServiceRecord(db.Model):
    __tablename__ = "service_records"

    TYPE_CHOICES = {
        "pnr":     "ПНР",
        "to":      "ТО",
        "repair":  "Ремонт",
        "request": "Заявка",
        "upgrade": "Модернизация",
        "other":   "Прочее",
    }

    STATUS_CHOICES = {
        "open":        "Открыта",
        "in_progress": "В работе",
        "done":        "Выполнено",
        "cancelled":   "Отменено",
    }

    id          = db.Column(db.Integer, primary_key=True)
    object_id   = db.Column(db.Integer, db.ForeignKey("service_objects.id"), nullable=False)
    record_type = db.Column(db.String(32), nullable=False, default="to")
    status      = db.Column(db.String(32), nullable=False, default="done")
    date        = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    description = db.Column(db.Text, nullable=False)
    result      = db.Column(db.Text, nullable=True)
    engineer_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    engineer    = db.relationship("User", foreign_keys=[engineer_id])
    next_to_date = db.Column(db.DateTime, nullable=True)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)
    created_by  = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    @property
    def type_label(self):
        return self.TYPE_CHOICES.get(self.record_type, self.record_type)

    @property
    def status_label(self):
        return self.STATUS_CHOICES.get(self.status, self.status)


class ObjectPassword(db.Model):
    __tablename__ = "object_passwords"

    id         = db.Column(db.Integer, primary_key=True)
    object_id  = db.Column(db.Integer, db.ForeignKey("service_objects.id"), nullable=False)
    title      = db.Column(db.String(128), nullable=False)
    login      = db.Column(db.String(128), nullable=True)
    password   = db.Column(db.String(256), nullable=False)
    ip_or_url  = db.Column(db.String(256), nullable=True)
    notes      = db.Column(db.String(512), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class ObjectFile(db.Model):
    __tablename__ = "object_files"

    TYPE_CHOICES = {
        "config":   "Конфигурация",
        "schema":   "Схема",
        "estimate": "Смета",
        "contract": "Договор",
        "act":      "Акт",
        "other":    "Прочее",
    }

    id            = db.Column(db.Integer, primary_key=True)
    object_id     = db.Column(db.Integer, db.ForeignKey("service_objects.id"), nullable=False)
    filename      = db.Column(db.String(256), nullable=False)
    original_name = db.Column(db.String(256), nullable=False)
    file_type     = db.Column(db.String(32), nullable=False, default="other")
    description   = db.Column(db.String(512), nullable=True)
    version       = db.Column(db.String(32), nullable=True)
    uploaded_at   = db.Column(db.DateTime, default=datetime.utcnow)
    uploaded_by   = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    author        = db.relationship("User", foreign_keys=[uploaded_by])

    @property
    def url(self):
        return f"/static/uploads/objects/{self.object_id}/{self.filename}"

    @property
    def type_label(self):
        return self.TYPE_CHOICES.get(self.file_type, self.file_type)


class ObjectEquipment(db.Model):
    __tablename__ = "object_equipment"

    id             = db.Column(db.Integer, primary_key=True)
    object_id      = db.Column(db.Integer, db.ForeignKey("service_objects.id"), nullable=False)
    name           = db.Column(db.String(256), nullable=False)
    model          = db.Column(db.String(256), nullable=True)
    serial_number  = db.Column(db.String(128), nullable=True)
    quantity       = db.Column(db.Integer, nullable=False, default=1)
    installed_at   = db.Column(db.DateTime, nullable=True)
    warranty_until = db.Column(db.DateTime, nullable=True)
    location       = db.Column(db.String(256), nullable=True)
    notes          = db.Column(db.String(512), nullable=True)

    @property
    def warranty_status(self):
        if not self.warranty_until:
            return None
        return "active" if self.warranty_until > datetime.utcnow() else "expired"