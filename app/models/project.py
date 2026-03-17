import os
from datetime import datetime
from app.extensions import db


class Project(db.Model):
    __tablename__ = "projects"

    STATUS_CHOICES = {
        "new":         "Новый",
        "design":      "Проектирование",
        "planning":    "Планирование",
        "in_progress": "Монтаж",
        "pnr":         "ПНР",
        "completed":   "Сдан",
        "on_hold":     "Приостановлен",
    }

    id             = db.Column(db.Integer, primary_key=True)
    name           = db.Column(db.String(256), nullable=False)
    address        = db.Column(db.String(512), nullable=True)
    client         = db.Column(db.String(256), nullable=True)
    description    = db.Column(db.Text, nullable=True)
    status         = db.Column(db.String(32), nullable=False, default="new")

    # Ответственные
    engineer_id    = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    designer_id    = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    created_by_id  = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    created_at     = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at     = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    started_at     = db.Column(db.DateTime, nullable=True)
    completed_at   = db.Column(db.DateTime, nullable=True)

    # Связи (существующие)
    engineer       = db.relationship("User", backref="projects",       foreign_keys=[engineer_id])
    designer       = db.relationship("User", backref="design_projects", foreign_keys=[designer_id])
    created_by     = db.relationship("User", backref="created_projects", foreign_keys=[created_by_id])

    checklist      = db.relationship("ChecklistItem", backref="project", lazy="select",
                                     cascade="all, delete-orphan", order_by="ChecklistItem.order")
    cable_journal  = db.relationship("CableJournal", backref="project", lazy="select",
                                     cascade="all, delete-orphan")
    ip_table       = db.relationship("IPTable", backref="project", lazy="select",
                                     cascade="all, delete-orphan")
    photos         = db.relationship("ProjectPhoto", backref="project", lazy="select",
                                     cascade="all, delete-orphan",
                                     order_by="ProjectPhoto.uploaded_at.desc()")
    notes          = db.relationship("ProjectNote", backref="project", lazy="select",
                                     cascade="all, delete-orphan",
                                     order_by="ProjectNote.created_at.desc()")

    # Новые связи
    documents      = db.relationship("ProjectDocument", backref="project", lazy="select",
                                     cascade="all, delete-orphan",
                                     order_by="ProjectDocument.uploaded_at.desc()")
    project_orders = db.relationship("ProjectOrder", backref="project", lazy="select",
                                     cascade="all, delete-orphan",
                                     order_by="ProjectOrder.created_at.desc()")

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

    def docs_by_type(self, doc_type: str):
        return [d for d in self.documents if d.doc_type == doc_type]

    def __repr__(self):
        return f"<Project {self.name}>"


# ─────────────────────────────────────────────────────────────────────────────
# Документация проектировщика
# ─────────────────────────────────────────────────────────────────────────────

class ProjectDocument(db.Model):
    """Файл документации, привязанный к проекту."""
    __tablename__ = "project_documents"

    # Типы блоков документации
    DOC_TYPES = {
        "plan":        "Планы",
        "autocad":     "AutoCAD (.dwg)",
        "pdf":         "PDF-документация",
        "executive":   "Исполнительная документация",
        "working":     "Рабочая документация",
        "estimate":    "Сметы / Спецификации",
    }

    # Иконки для каждого типа (emoji для простоты)
    DOC_ICONS = {
        "plan":      "🗺",
        "autocad":   "📐",
        "pdf":       "📄",
        "executive": "📋",
        "working":   "📁",
        "estimate":  "📊",
    }

    id            = db.Column(db.Integer, primary_key=True)
    project_id    = db.Column(db.Integer, db.ForeignKey("projects.id"), nullable=False)
    doc_type      = db.Column(db.String(32), nullable=False)          # ключ из DOC_TYPES
    title         = db.Column(db.String(256), nullable=False)         # название документа
    filename      = db.Column(db.String(256), nullable=False)         # имя файла на диске
    original_name = db.Column(db.String(256), nullable=False)         # оригинальное имя
    file_size     = db.Column(db.Integer, nullable=True)              # байты
    version       = db.Column(db.String(32), nullable=True)           # версия/ревизия
    notes         = db.Column(db.String(512), nullable=True)
    uploaded_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    uploaded_at   = db.Column(db.DateTime, default=datetime.utcnow)

    uploaded_by   = db.relationship("User", foreign_keys=[uploaded_by_id])

    @property
    def doc_type_label(self):
        return self.DOC_TYPES.get(self.doc_type, self.doc_type)

    @property
    def doc_icon(self):
        return self.DOC_ICONS.get(self.doc_type, "📎")

    @property
    def url(self):
        return f"/static/uploads/projects/{self.project_id}/docs/{self.filename}"

    @property
    def file_size_human(self):
        if not self.file_size:
            return ""
        if self.file_size < 1024:
            return f"{self.file_size} Б"
        if self.file_size < 1024 * 1024:
            return f"{self.file_size // 1024} КБ"
        return f"{self.file_size / (1024*1024):.1f} МБ"

    @property
    def ext(self):
        return self.original_name.rsplit(".", 1)[-1].lower() if "." in self.original_name else ""

    def __repr__(self):
        return f"<ProjectDocument {self.doc_type}:{self.title}>"


# ─────────────────────────────────────────────────────────────────────────────
# Заказы офиса — привязка Order склада к проекту
# ─────────────────────────────────────────────────────────────────────────────

class ProjectOrder(db.Model):
    """Связь заказа склада с проектом. Офис создаёт заказ прямо из проекта."""
    __tablename__ = "project_orders"

    id         = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id"), nullable=False)
    order_id   = db.Column(db.Integer, db.ForeignKey("orders.id"),   nullable=False)
    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    notes      = db.Column(db.String(256), nullable=True)

    order      = db.relationship("Order", foreign_keys=[order_id])
    created_by = db.relationship("User", foreign_keys=[created_by_id])

    def __repr__(self):
        return f"<ProjectOrder project={self.project_id} order={self.order_id}>"


# ─────────────────────────────────────────────────────────────────────────────
# Существующие модели (без изменений)
# ─────────────────────────────────────────────────────────────────────────────

class ChecklistItem(db.Model):
    __tablename__ = "checklist_items"

    CATEGORIES = {
        "preparation":   "Подготовка",
        "installation":  "Монтаж",
        "cabling":       "Кабельные работы",
        "commissioning": "Пуско-наладка",
        "documentation": "Документация",
        "handover":      "Сдача объекта",
    }

    id         = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id"), nullable=False)
    title      = db.Column(db.String(256), nullable=False)
    category   = db.Column(db.String(64), nullable=False, default="installation")
    is_done    = db.Column(db.Boolean, default=False)
    order      = db.Column(db.Integer, default=0)
    done_at    = db.Column(db.DateTime, nullable=True)
    done_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    notes      = db.Column(db.String(512), nullable=True)

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

    id         = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id"), nullable=False)
    number     = db.Column(db.String(32), nullable=False)
    cable_type = db.Column(db.String(128), nullable=False)
    from_point = db.Column(db.String(256), nullable=False)
    to_point   = db.Column(db.String(256), nullable=False)
    length     = db.Column(db.Float, nullable=True)
    section    = db.Column(db.String(32), nullable=True)
    status     = db.Column(db.String(32), nullable=False, default="planned")
    notes      = db.Column(db.String(512), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

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

    id           = db.Column(db.Integer, primary_key=True)
    project_id   = db.Column(db.Integer, db.ForeignKey("projects.id"), nullable=False)
    ip_address   = db.Column(db.String(64), nullable=False)
    mac_address  = db.Column(db.String(32), nullable=True)
    device_name  = db.Column(db.String(256), nullable=False)
    device_model = db.Column(db.String(256), nullable=True)
    location     = db.Column(db.String(256), nullable=True)
    login        = db.Column(db.String(128), nullable=True)
    password     = db.Column(db.String(128), nullable=True)
    status       = db.Column(db.String(32), nullable=False, default="active")
    notes        = db.Column(db.String(512), nullable=True)
    created_at   = db.Column(db.DateTime, default=datetime.utcnow)

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