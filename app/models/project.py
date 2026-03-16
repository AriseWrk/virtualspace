import os
from datetime import datetime
from app.extensions import db


class Project(db.Model):
    __tablename__ = "projects"

    STATUS_CHOICES = {
        "planning":    "Планирование",
        "in_progress": "В работе",
        "on_hold":     "Приостановлен",
        "completed":   "Завершён",
    }

    id            = db.Column(db.Integer, primary_key=True)
    name          = db.Column(db.String(256), nullable=False)
    address       = db.Column(db.String(512), nullable=True)
    client        = db.Column(db.String(256), nullable=True)
    description   = db.Column(db.Text, nullable=True)
    status        = db.Column(db.String(32), nullable=False, default="planning")
    engineer_id   = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at    = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    started_at    = db.Column(db.DateTime, nullable=True)
    completed_at  = db.Column(db.DateTime, nullable=True)

    # Связи
    engineer      = db.relationship("User", backref="projects", foreign_keys=[engineer_id])
    checklist     = db.relationship("ChecklistItem", backref="project", lazy="select",
                                    cascade="all, delete-orphan", order_by="ChecklistItem.order")
    cable_journal = db.relationship("CableJournal", backref="project", lazy="select",
                                    cascade="all, delete-orphan")
    ip_table      = db.relationship("IPTable", backref="project", lazy="select",
                                    cascade="all, delete-orphan")
    photos        = db.relationship("ProjectPhoto", backref="project", lazy="select",
                                    cascade="all, delete-orphan", order_by="ProjectPhoto.uploaded_at.desc()")
    notes         = db.relationship("ProjectNote", backref="project", lazy="select",
                                    cascade="all, delete-orphan", order_by="ProjectNote.created_at.desc()")

    @property
    def status_label(self):
        return self.STATUS_CHOICES.get(self.status, self.status)

    @property
    def checklist_progress(self):
        total = len(self.checklist)
        if total == 0:
            return 0
        done = sum(1 for item in self.checklist if item.is_done)
        return int(done / total * 100)

    @property
    def checklist_done(self):
        return sum(1 for item in self.checklist if item.is_done)

    def __repr__(self):
        return f"<Project {self.name}>"


class ChecklistItem(db.Model):
    __tablename__ = "checklist_items"

    CATEGORIES = {
        "preparation":  "Подготовка",
        "installation": "Монтаж",
        "cabling":      "Кабельные работы",
        "commissioning":"Пуско-наладка",
        "documentation":"Документация",
        "handover":     "Сдача объекта",
    }

    id          = db.Column(db.Integer, primary_key=True)
    project_id  = db.Column(db.Integer, db.ForeignKey("projects.id"), nullable=False)
    title       = db.Column(db.String(256), nullable=False)
    category    = db.Column(db.String(64), nullable=False, default="installation")
    is_done     = db.Column(db.Boolean, default=False)
    order       = db.Column(db.Integer, default=0)
    done_at     = db.Column(db.DateTime, nullable=True)
    done_by_id  = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    notes       = db.Column(db.String(512), nullable=True)

    done_by = db.relationship("User", foreign_keys=[done_by_id])

    @property
    def category_label(self):
        return self.CATEGORIES.get(self.category, self.category)


class CableJournal(db.Model):
    __tablename__ = "cable_journal"

    STATUS_CHOICES = {
        "planned":   "Запланирован",
        "laid":      "Проложен",
        "connected": "Подключён",
        "tested":    "Протестирован",
    }

    id          = db.Column(db.Integer, primary_key=True)
    project_id  = db.Column(db.Integer, db.ForeignKey("projects.id"), nullable=False)
    number      = db.Column(db.String(32), nullable=False)
    cable_type  = db.Column(db.String(128), nullable=False)
    from_point  = db.Column(db.String(256), nullable=False)
    to_point    = db.Column(db.String(256), nullable=False)
    length      = db.Column(db.Float, nullable=True)
    section     = db.Column(db.String(32), nullable=True)
    status      = db.Column(db.String(32), nullable=False, default="planned")
    notes       = db.Column(db.String(512), nullable=True)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def status_label(self):
        return self.STATUS_CHOICES.get(self.status, self.status)


class IPTable(db.Model):
    __tablename__ = "ip_table"

    STATUS_CHOICES = {
        "active":   "Активен",
        "inactive": "Неактивен",
        "reserved": "Зарезервирован",
    }

    id          = db.Column(db.Integer, primary_key=True)
    project_id  = db.Column(db.Integer, db.ForeignKey("projects.id"), nullable=False)
    ip_address  = db.Column(db.String(64), nullable=False)
    mac_address = db.Column(db.String(32), nullable=True)
    device_name = db.Column(db.String(256), nullable=False)
    device_model= db.Column(db.String(256), nullable=True)
    location    = db.Column(db.String(256), nullable=True)
    login       = db.Column(db.String(128), nullable=True)
    password    = db.Column(db.String(128), nullable=True)
    status      = db.Column(db.String(32), nullable=False, default="active")
    notes       = db.Column(db.String(512), nullable=True)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def status_label(self):
        return self.STATUS_CHOICES.get(self.status, self.status)


class ProjectPhoto(db.Model):
    __tablename__ = "project_photos"

    id          = db.Column(db.Integer, primary_key=True)
    project_id  = db.Column(db.Integer, db.ForeignKey("projects.id"), nullable=False)
    filename    = db.Column(db.String(256), nullable=False)
    description = db.Column(db.String(512), nullable=True)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    uploaded_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    author = db.relationship("User", foreign_keys=[uploaded_by])

    @property
    def url(self):
        return f"/static/uploads/projects/{self.project_id}/{self.filename}"


class ProjectNote(db.Model):
    __tablename__ = "project_notes"

    TYPE_CHOICES = {
        "note":    "Заметка",
        "problem": "Проблема",
        "task":    "Задача",
        "info":    "Информация",
    }

    id         = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id"), nullable=False)
    text       = db.Column(db.Text, nullable=False)
    note_type  = db.Column(db.String(32), nullable=False, default="note")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    author_id  = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    author = db.relationship("User", foreign_keys=[author_id])

    @property
    def type_label(self):
        return self.TYPE_CHOICES.get(self.note_type, self.note_type)