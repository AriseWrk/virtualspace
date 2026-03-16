from flask import Blueprint, render_template
from flask_login import login_required, current_user
from flask import redirect, url_for, flash
from functools import wraps

designer_bp = Blueprint("designer", __name__, url_prefix="/designer")


def designer_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if current_user.role not in ("designer", "director"):
            flash("Доступ запрещён.", "error")
            return redirect(url_for("dashboard.index"))
        return f(*args, **kwargs)
    return login_required(decorated)


@designer_bp.route("/")
@designer_required
def dashboard():
    return render_template("designer/dashboard.html")


@designer_bp.route("/projects")
@designer_required
def projects():
    return render_template("designer/projects.html")


@designer_bp.route("/autocad")
@designer_required
def autocad():
    scripts = [
        {
            "name": "Нумерация кабелей",
            "description": "Автоматическая нумерация кабельных трасс на чертеже по заданному шаблону",
            "type": "AutoLISP",
            "ext": ".lsp",
            "filename": "cable_numbering.lsp",
        },
        {
            "name": "Расстановка УГО СКС",
            "description": "Вставка условных графических обозначений элементов СКС из библиотеки блоков",
            "type": "AutoLISP",
            "ext": ".lsp",
            "filename": "scs_ugo.lsp",
        },
        {
            "name": "Спецификация из чертежа",
            "description": "Автоматическое формирование таблицы спецификации на основе атрибутов блоков",
            "type": "Script",
            "ext": ".scr",
            "filename": "spec_export.scr",
        },
        {
            "name": "Очистка слоёв",
            "description": "Удаление пустых и неиспользуемых слоёв, стандартизация имён по ГОСТ",
            "type": "AutoLISP",
            "ext": ".lsp",
            "filename": "layer_cleanup.lsp",
        },
        {
            "name": "Штамп проектной документации",
            "description": "Вставка и заполнение основной надписи по ГОСТ 21.1101-2013",
            "type": "AutoLISP",
            "ext": ".lsp",
            "filename": "stamp_fill.lsp",
        },
    ]
    return render_template("designer/autocad.html", scripts=scripts)


@designer_bp.route("/regulations")
@designer_required
def regulations():
    docs = [
        {"name": "Структурированные кабельные системы", "number": "ГОСТ Р 58139-2018", "category": "СКС"},
        {"name": "Охранная сигнализация. Проектирование", "number": "СП 484.1311500.2020", "category": "ОС"},
        {"name": "Системы видеонаблюдения", "number": "СП 486.1311500.2020", "category": "CCTV"},
        {"name": "СКУД. Требования к системам", "number": "ГОСТ Р 51241-2008", "category": "СКУД"},
        {"name": "Пожарная сигнализация", "number": "СП 484.1311500.2020", "category": "ПС"},
        {"name": "Электроустановки зданий", "number": "ГОСТ Р 50571-2013", "category": "ЭУ"},
        {"name": "Условные обозначения в документации", "number": "ГОСТ 21.1101-2013", "category": "ГОСТ"},
        {"name": "Оформление проектной документации", "number": "ГОСТ Р 21.1101-2009", "category": "ГОСТ"},
    ]
    return render_template("designer/regulations.html", docs=docs)


@designer_bp.route("/blocks")
@designer_required
def blocks():
    return render_template("designer/blocks.html")


@designer_bp.route("/equipment")
@designer_required
def equipment():
    return render_template("designer/equipment.html")