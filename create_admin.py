"""
Запустить ОДИН РАЗ для создания первого администратора:
    python create_admin.py
"""
from app import create_app
from app.extensions import db
from app.models.user import User

app = create_app()

with app.app_context():
    db.create_all()

    if User.query.filter_by(username='admin').first():
        print("Пользователь admin уже существует.")
    else:
        admin = User(
            username='admin',
            full_name='Администратор',
            role='director',
        )
        admin.set_password('Admin1234!')
        db.session.add(admin)
        db.session.commit()
        print("Создан: admin / Admin1234!")
        print("Смените пароль после первого входа!")
