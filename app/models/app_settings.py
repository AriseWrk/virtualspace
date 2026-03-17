from app.extensions import db


class AppSettings(db.Model):
    """Настройки приложения — хранятся в БД, управляются из админки."""
    __tablename__ = "app_settings"

    id    = db.Column(db.Integer, primary_key=True)
    key   = db.Column(db.String(64), unique=True, nullable=False)
    value = db.Column(db.Text, nullable=True)
    label = db.Column(db.String(128), nullable=True)   # человекочитаемое название

    @classmethod
    def get(cls, key: str, default: str = "") -> str:
        row = cls.query.filter_by(key=key).first()
        return row.value if row and row.value else default

    @classmethod
    def set(cls, key: str, value: str, label: str = None):
        row = cls.query.filter_by(key=key).first()
        if row:
            row.value = value
        else:
            row = cls(key=key, value=value, label=label)
            db.session.add(row)

    def __repr__(self):
        return f"<AppSettings {self.key}={self.value!r}>"