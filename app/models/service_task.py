import os
from datetime import datetime
from app.extensions import db


class ServiceTask(db.Model):
    """План-задание сервисной службы."""
    __tablename__ = "service_tasks"

    WORK_TYPES = {
        "to":       "Техническое обслуживание",
        "repair":   "Ремонт",
        "mounting": "Монтаж",
        "visit":    "Выезд / осмотр",
        "other":    "Прочее",
    }

    PRIORITIES = {
        "urgent": "Срочно",
        "normal": "Обычный",
    }

    STATUS_CHOICES = {
        "new":        "Новое",
        "assigned":   "Назначено",
        "in_progress":"Выполняется",
        "done":       "Выполнено",
        "failed":     "Не выполнено",
        "cancelled":  "Отменено",
    }

    id              = db.Column(db.Integer, primary_key=True)
    number          = db.Column(db.String(32), unique=True, nullable=False)

    # Объект — либо из ПТС, либо вручную
    object_id       = db.Column(db.Integer, db.ForeignKey("service_objects.id"), nullable=True)
    object_name     = db.Column(db.String(256), nullable=False)   # всегда заполнено
    object_address  = db.Column(db.String(512), nullable=True)

    work_type       = db.Column(db.String(32), nullable=False, default="to")
    priority        = db.Column(db.String(16), nullable=False, default="normal")
    status          = db.Column(db.String(32), nullable=False, default="new")

    planned_date    = db.Column(db.DateTime, nullable=True)        # плановая дата
    description     = db.Column(db.Text, nullable=True)           # задача

    # Файл/фото от офиса
    attachment      = db.Column(db.String(256), nullable=True)    # имя файла на диске
    attachment_name = db.Column(db.String(256), nullable=True)    # оригинальное имя

    created_by_id   = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at      = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at      = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Связи
    service_object  = db.relationship("ServiceObject", foreign_keys=[object_id])
    created_by      = db.relationship("User", foreign_keys=[created_by_id])
    engineers       = db.relationship("ServiceTaskEngineer", backref="task",
                                      cascade="all, delete-orphan", lazy="select")
    report          = db.relationship("ServiceTaskReport", backref="task",
                                      uselist=False, cascade="all, delete-orphan")

    @property
    def work_type_label(self):
        return self.WORK_TYPES.get(self.work_type, self.work_type)

    @property
    def priority_label(self):
        return self.PRIORITIES.get(self.priority, self.priority)

    @property
    def status_label(self):
        return self.STATUS_CHOICES.get(self.status, self.status)

    @property
    def is_urgent(self):
        return self.priority == "urgent"

    @property
    def attachment_url(self):
        if self.attachment:
            return f"/static/uploads/service_tasks/{self.id}/{self.attachment}"
        return None

    def __repr__(self):
        return f"<ServiceTask {self.number}>"


class ServiceTaskEngineer(db.Model):
    """Инженеры, назначенные на план-задание (один или несколько)."""
    __tablename__ = "service_task_engineers"

    id          = db.Column(db.Integer, primary_key=True)
    task_id     = db.Column(db.Integer, db.ForeignKey("service_tasks.id"), nullable=False)
    engineer_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    engineer    = db.relationship("User", foreign_keys=[engineer_id])


class ServiceTaskReport(db.Model):
    """Отчёт сервисной службы по план-заданию."""
    __tablename__ = "service_task_reports"

    VERDICT_CHOICES = {
        "done":         "Выполнено в полном объёме",
        "partial":      "Выполнено частично",
        "failed":       "Не выполнено",
        "rescheduled":  "Перенесено",
    }

    id              = db.Column(db.Integer, primary_key=True)
    task_id         = db.Column(db.Integer, db.ForeignKey("service_tasks.id"), nullable=False)

    arrived_at      = db.Column(db.DateTime, nullable=True)    # фактическое время прибытия
    departed_at     = db.Column(db.DateTime, nullable=True)    # фактическое время убытия
    verdict         = db.Column(db.String(32), nullable=True)  # ключ из VERDICT_CHOICES
    notes           = db.Column(db.Text, nullable=True)        # комментарий сервиса

    # Файл/фото от сервиса
    attachment      = db.Column(db.String(256), nullable=True)
    attachment_name = db.Column(db.String(256), nullable=True)

    filled_by_id    = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    filled_at       = db.Column(db.DateTime, nullable=True)

    filled_by       = db.relationship("User", foreign_keys=[filled_by_id])

    @property
    def verdict_label(self):
        return self.VERDICT_CHOICES.get(self.verdict, self.verdict or "—")

    @property
    def duration_minutes(self):
        if self.arrived_at and self.departed_at:
            delta = self.departed_at - self.arrived_at
            return int(delta.total_seconds() / 60)
        return None

    @property
    def attachment_url(self):
        if self.attachment:
            return f"/static/uploads/service_tasks/{self.task_id}/report_{self.attachment}"
        return None

    def __repr__(self):
        return f"<ServiceTaskReport task={self.task_id} verdict={self.verdict}>"