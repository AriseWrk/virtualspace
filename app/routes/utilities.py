from flask import Blueprint, render_template
from flask_login import login_required

utilities_bp = Blueprint("utilities", __name__, url_prefix="/utilities")


@utilities_bp.route("/")
@login_required
def dashboard():
    tools = [
        {
            "name": "Калькулятор кабеля",
            "desc": "Расчёт длины, сечения и потерь для кабельных трасс",
            "icon": "🔌",
            "url": "calc_cable",
            "ready": True,
        },
        {
            "name": "Калькулятор IP-подсети",
            "desc": "Разбивка на подсети, маски, диапазоны адресов",
            "icon": "🌐",
            "url": "calc_ip",
            "ready": True,
        },
        {
            "name": "Калькулятор мощности UPS",
            "desc": "Подбор ИБП по нагрузке и времени автономной работы",
            "icon": "⚡",
            "url": "calc_ups",
            "ready": True,
        },
        {
            "name": "Конвертер единиц",
            "desc": "dBm/mW, AWG/мм², футы/метры и другие",
            "icon": "🔄",
            "url": "calc_convert",
            "ready": True,
        },
    ]
    software = [
        {"name": "Putty", "desc": "SSH/Telnet клиент", "version": "0.80", "ext": ".exe"},
        {"name": "WinSCP", "desc": "SFTP/FTP клиент", "version": "6.1", "ext": ".exe"},
        {"name": "Wireshark", "desc": "Анализатор трафика", "version": "4.2", "ext": ".exe"},
        {"name": "Advanced IP Scanner", "desc": "Сканер сети", "version": "2.5", "ext": ".exe"},
        {"name": "NetScan", "desc": "Мониторинг сети", "version": "3.1", "ext": ".exe"},
        {"name": "MobaXterm", "desc": "Терминал + SSH + X11", "version": "23.4", "ext": ".exe"},
    ]
    return render_template("utilities/dashboard.html", tools=tools, software=software)


@utilities_bp.route("/calc/cable")
@login_required
def calc_cable():
    return render_template("utilities/calc_cable.html")


@utilities_bp.route("/calc/ip")
@login_required
def calc_ip():
    return render_template("utilities/calc_ip.html")


@utilities_bp.route("/calc/ups")
@login_required
def calc_ups():
    return render_template("utilities/calc_ups.html")


@utilities_bp.route("/calc/convert")
@login_required
def calc_convert():
    return render_template("utilities/calc_convert.html")