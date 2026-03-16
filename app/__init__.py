from flask import Flask
from config import config
from app.extensions import db, login_manager, migrate


def create_app(config_name="default"):
    app = Flask(__name__)
    app.config.from_object(config[config_name])

    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)

    from app.routes.auth import auth_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.warehouse import warehouse_bp
    from app.routes.admin import admin_bp
    from app.routes.engineer import engineer_bp
    from app.routes.designer import designer_bp
    from app.routes.academy import academy_bp
    from app.routes.utilities import utilities_bp
    from app.routes.server_room import server_room_bp
    from app.routes.garage import garage_bp
    from app.routes.pts import pts_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(warehouse_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(engineer_bp)
    app.register_blueprint(designer_bp)
    app.register_blueprint(academy_bp)
    app.register_blueprint(utilities_bp)
    app.register_blueprint(server_room_bp)
    app.register_blueprint(garage_bp)
    app.register_blueprint(pts_bp)

    return app