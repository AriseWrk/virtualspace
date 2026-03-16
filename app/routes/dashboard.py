from flask import Blueprint, render_template
from flask_login import login_required, current_user
from app.models.warehouse import Item
from app.models.order import Order

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/")
@login_required
def index():
    total_items = Item.query.count()
    low_stock_items = [i for i in Item.query.all() if i.is_low_stock]
    open_orders = Order.query.filter(
        Order.status.in_(["new", "in_progress"])
    ).count()
    recent_orders = Order.query.order_by(Order.created_at.desc()).limit(5).all()

    stats = {
        "total_items": total_items,
        "low_stock_count": len(low_stock_items),
        "open_orders": open_orders,
    }

    return render_template(
        "dashboard/index.html",
        stats=stats,
        recent_orders=recent_orders,
    )