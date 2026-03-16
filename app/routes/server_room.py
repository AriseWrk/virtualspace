from flask import Blueprint, render_template
from flask_login import login_required, current_user
from flask import redirect, url_for, flash
from functools import wraps
from app.extensions import db
from sqlalchemy import text

server_room_bp = Blueprint("server_room", __name__, url_prefix="/server")


def server_access(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if current_user.role not in ("director", "engineer", "designer"):
            flash("Доступ запрещён.", "error")
            return redirect(url_for("dashboard.index"))
        return f(*args, **kwargs)
    return login_required(decorated)


def get_db_stats():
    """Получаем статистику PostgreSQL."""
    try:
        stats = {}

        # Размер БД
        result = db.session.execute(text(
            "SELECT pg_size_pretty(pg_database_size(current_database())) as size,"
            "pg_database_size(current_database()) as size_bytes"
        )).fetchone()
        stats["db_size"] = result.size
        stats["db_size_bytes"] = result.size_bytes

        # Активные соединения
        result = db.session.execute(text(
            "SELECT count(*) as cnt FROM pg_stat_activity "
            "WHERE datname = current_database()"
        )).fetchone()
        stats["connections"] = result.cnt

        # Макс. соединений
        result = db.session.execute(text(
            "SELECT setting::int as max_conn FROM pg_settings "
            "WHERE name = 'max_connections'"
        )).fetchone()
        stats["max_connections"] = result.max_conn

        # Версия PostgreSQL
        result = db.session.execute(text(
            "SELECT version()"
        )).fetchone()
        stats["pg_version"] = result.version.split(",")[0]

        # Статистика по таблицам нашей БД
        tables = db.session.execute(text("""
            SELECT
                relname AS table_name,
                n_live_tup AS row_count,
                pg_size_pretty(pg_total_relation_size(relid)) AS total_size,
                pg_total_relation_size(relid) AS size_bytes,
                n_dead_tup AS dead_rows,
                last_vacuum,
                last_autovacuum,
                last_analyze
            FROM pg_stat_user_tables
            ORDER BY n_live_tup DESC
        """)).fetchall()
        stats["tables"] = tables

        # Транзакции
        result = db.session.execute(text("""
            SELECT
                xact_commit AS commits,
                xact_rollback AS rollbacks,
                blks_read,
                blks_hit,
                CASE WHEN (blks_hit + blks_read) > 0
                    THEN round(blks_hit::numeric / (blks_hit + blks_read) * 100, 1)
                    ELSE 0
                END AS cache_hit_ratio
            FROM pg_stat_database
            WHERE datname = current_database()
        """)).fetchone()
        stats["transactions"] = result

        # Долгие запросы (> 1 сек)
        slow_queries = db.session.execute(text("""
            SELECT
                pid,
                now() - pg_stat_activity.query_start AS duration,
                query,
                state
            FROM pg_stat_activity
            WHERE datname = current_database()
              AND state != 'idle'
              AND (now() - pg_stat_activity.query_start) > interval '1 second'
            ORDER BY duration DESC
            LIMIT 5
        """)).fetchall()
        stats["slow_queries"] = slow_queries

        stats["error"] = None

    except Exception as e:
        stats = {"error": str(e)}

    return stats


@server_room_bp.route("/")
@server_access
def dashboard():
    servers = [
        {"name": "SRV-MAIN-01",   "role": "Основной сервер",    "ip": "192.168.1.10", "status": "online",  "os": "Ubuntu 22.04"},
        {"name": "SRV-BACKUP-01", "role": "Резервный сервер",   "ip": "192.168.1.11", "status": "online",  "os": "Ubuntu 22.04"},
        {"name": "SRV-DB-01",     "role": "База данных",        "ip": "192.168.1.12", "status": "online",  "os": "Debian 12"},
        {"name": "NAS-01",        "role": "Сетевое хранилище",  "ip": "192.168.1.20", "status": "online",  "os": "TrueNAS"},
        {"name": "SW-CORE-01",    "role": "Коммутатор ядра",    "ip": "192.168.1.1",  "status": "online",  "os": "Cisco IOS"},
        {"name": "FW-01",         "role": "Межсетевой экран",   "ip": "192.168.1.2",  "status": "online",  "os": "pfSense"},
    ]
    db_stats = get_db_stats()
    return render_template("server_room/dashboard.html", servers=servers, db_stats=db_stats)


@server_room_bp.route("/db")
@server_access
def db_monitor():
    db_stats = get_db_stats()
    return render_template("server_room/db_monitor.html", db_stats=db_stats)


@server_room_bp.route("/docs")
@server_access
def docs():
    return render_template("server_room/docs.html")


@server_room_bp.route("/network")
@server_access
def network():
    return render_template("server_room/network.html")