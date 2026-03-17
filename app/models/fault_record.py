from datetime import datetime
from app.extensions import db


class FaultRecord(db.Model):
    """База неисправностей — инженер фиксирует проблему и решение."""
    __tablename__ = "fault_records"

    CATEGORIES = {
        "cctv":     "Видеонаблюдение",
        "access":   "СКУД",
        "fire":     "Пожарная сигнализация",
        "network":  "Сеть / СКС",
        "power":    "Электропитание",
        "software": "ПО / Прошивки",
        "other":    "Прочее",
    }

    id           = db.Column(db.Integer, primary_key=True)
    title        = db.Column(db.String(256), nullable=False)       # Заголовок проблемы
    category     = db.Column(db.String(32),  nullable=False, default="other")
    symptoms     = db.Column(db.Text,        nullable=False)       # Симптомы / описание
    solution     = db.Column(db.Text,        nullable=False)       # Решение
    equipment    = db.Column(db.String(256), nullable=True)        # Марка/модель оборудования
    tags         = db.Column(db.String(512), nullable=True)        # Теги через запятую
    is_public    = db.Column(db.Boolean,     default=True)         # Видят все или только автор
    views        = db.Column(db.Integer,     default=0)

    author_id    = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at   = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at   = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    author       = db.relationship("User", foreign_keys=[author_id])

    @property
    def category_label(self):
        return self.CATEGORIES.get(self.category, self.category)

    @property
    def tag_list(self):
        if self.tags:
            return [t.strip() for t in self.tags.split(",") if t.strip()]
        return []

    def __repr__(self):
        return f"<FaultRecord {self.title}>"