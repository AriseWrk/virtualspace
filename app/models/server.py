from app.extensions import db


class MonitoredServer(db.Model):
    __tablename__ = 'monitored_servers'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(100))
    ip = db.Column(db.String(50), nullable=False)
    os = db.Column(db.String(50))
    status = db.Column(db.String(20), default='checking')

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "role": self.role,
            "ip": self.ip,
            "os": self.os,
            "status": self.status
        }