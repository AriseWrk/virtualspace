from datetime import datetime
from app.extensions import db


class Category(db.Model):
    __tablename__ = "categories"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False, unique=True)
    description = db.Column(db.Text, nullable=True)
    items = db.relationship("Item", backref="category", lazy="dynamic")

    def __repr__(self):
        return f"<Category {self.name}>"


class Item(db.Model):
    __tablename__ = "items"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(256), nullable=False)
    article = db.Column(db.String(64), nullable=True, unique=True)
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=True)
    unit = db.Column(db.String(32), nullable=False, default="шт")

    # Остатки
    quantity = db.Column(db.Float, nullable=False, default=0.0)
    reserved_qty = db.Column(db.Float, nullable=False, default=0.0)   # зарезервировано (заказы)
    incoming_qty = db.Column(db.Float, nullable=False, default=0.0)   # ожидается приход

    min_quantity = db.Column(db.Float, nullable=False, default=0.0)

    # Цены
    cost_price = db.Column(db.Float, nullable=True, default=0.0)       # себестоимость (средняя)
    sale_price = db.Column(db.Float, nullable=True, default=0.0)       # цена продажи

    location = db.Column(db.String(128), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Связи
    order_items = db.relationship("OrderItem", backref="item", lazy="dynamic")
    movements = db.relationship("StockMovement", backref="item", lazy="dynamic",
                                foreign_keys="StockMovement.item_id")

    @property
    def available_qty(self) -> float:
        """Доступно = остаток - резерв"""
        return max(self.quantity - self.reserved_qty, 0.0)

    @property
    def is_low_stock(self) -> bool:
        return self.quantity <= self.min_quantity

    @property
    def total_cost(self) -> float:
        return (self.cost_price or 0.0) * self.quantity

    @property
    def total_sale(self) -> float:
        return (self.sale_price or 0.0) * self.quantity

    def __repr__(self):
        return f"<Item {self.name} ({self.quantity} {self.unit})>"


# ---------------------------------------------------------------------------
# Движения склада: приход / расход / перемещение
# ---------------------------------------------------------------------------

class StockMovement(db.Model):
    """
    Универсальная запись движения товара.
    move_type:
        receipt    — приходование (от поставщика)
        write_off  — списание
        transfer   — перемещение (между местами)
        order_out  — выдача по заказу (авто)
        adjustment — корректировка при инвентаризации
    """
    __tablename__ = "stock_movements"

    TYPES = {
        "receipt":    "Приход",
        "write_off":  "Списание",
        "transfer":   "Перемещение",
        "order_out":  "Выдача по заказу",
        "adjustment": "Корректировка",
    }

    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey("items.id"), nullable=False)
    move_type = db.Column(db.String(32), nullable=False)

    quantity = db.Column(db.Float, nullable=False)          # + приход, - расход
    unit_cost = db.Column(db.Float, nullable=True)          # себестоимость единицы на момент движения

    # Для перемещений
    from_location = db.Column(db.String(128), nullable=True)
    to_location = db.Column(db.String(128), nullable=True)

    # Ссылка на заказ (если order_out)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=True)

    # Ссылка на документ-источник
    document_ref = db.Column(db.String(128), nullable=True)  # номер накладной / акта
    notes = db.Column(db.Text, nullable=True)

    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    created_by = db.relationship("User", foreign_keys=[created_by_id])
    order = db.relationship("Order", foreign_keys=[order_id])

    @property
    def type_label(self) -> str:
        return self.TYPES.get(self.move_type, self.move_type)

    @property
    def total_cost(self) -> float:
        return (self.unit_cost or 0.0) * abs(self.quantity)

    def __repr__(self):
        return f"<StockMovement {self.move_type} item={self.item_id} qty={self.quantity}>"


# ---------------------------------------------------------------------------
# Приходование (Receipt) — заголовочный документ для группы движений
# ---------------------------------------------------------------------------

class Receipt(db.Model):
    """Документ прихода товара (один приход может содержать много позиций)."""
    __tablename__ = "receipts"

    STATUS_CHOICES = {
        "draft":     "Черновик",
        "confirmed": "Проведён",
        "cancelled": "Отменён",
    }

    id = db.Column(db.Integer, primary_key=True)
    number = db.Column(db.String(32), unique=True, nullable=False)
    supplier = db.Column(db.String(256), nullable=True)
    status = db.Column(db.String(32), nullable=False, default="draft")
    notes = db.Column(db.Text, nullable=True)
    receipt_date = db.Column(db.DateTime, nullable=True)

    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    items = db.relationship("ReceiptItem", backref="receipt", lazy="select",
                            cascade="all, delete-orphan")
    created_by = db.relationship("User", foreign_keys=[created_by_id])

    @property
    def status_label(self) -> str:
        return self.STATUS_CHOICES.get(self.status, self.status)

    @property
    def total_items(self) -> int:
        return len(self.items)

    @property
    def total_sum(self) -> float:
        return sum((i.quantity * (i.unit_cost or 0)) for i in self.items)

    def __repr__(self):
        return f"<Receipt {self.number} [{self.status}]>"


class ReceiptItem(db.Model):
    __tablename__ = "receipt_items"

    id = db.Column(db.Integer, primary_key=True)
    receipt_id = db.Column(db.Integer, db.ForeignKey("receipts.id"), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey("items.id"), nullable=False)
    quantity = db.Column(db.Float, nullable=False)
    unit_cost = db.Column(db.Float, nullable=True, default=0.0)

    item = db.relationship("Item")


# ---------------------------------------------------------------------------
# Списание (WriteOff) — заголовочный документ
# ---------------------------------------------------------------------------

class WriteOff(db.Model):
    """Документ списания товара."""
    __tablename__ = "write_offs"

    REASON_CHOICES = {
        "damage":      "Порча",
        "loss":        "Недостача",
        "expired":     "Истёк срок",
        "used":        "Использовано",
        "other":       "Прочее",
    }

    STATUS_CHOICES = {
        "draft":     "Черновик",
        "confirmed": "Проведён",
        "cancelled": "Отменён",
    }

    id = db.Column(db.Integer, primary_key=True)
    number = db.Column(db.String(32), unique=True, nullable=False)
    reason = db.Column(db.String(32), nullable=False, default="other")
    status = db.Column(db.String(32), nullable=False, default="draft")
    notes = db.Column(db.Text, nullable=True)

    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    items = db.relationship("WriteOffItem", backref="write_off", lazy="select",
                            cascade="all, delete-orphan")
    created_by = db.relationship("User", foreign_keys=[created_by_id])

    @property
    def reason_label(self) -> str:
        return self.REASON_CHOICES.get(self.reason, self.reason)

    @property
    def status_label(self) -> str:
        return self.STATUS_CHOICES.get(self.status, self.status)

    @property
    def total_items(self) -> int:
        return len(self.items)

    @property
    def total_sum(self) -> float:
        return sum((i.quantity * (i.item.cost_price or 0)) for i in self.items if i.item)

    def __repr__(self):
        return f"<WriteOff {self.number} [{self.status}]>"


class WriteOffItem(db.Model):
    __tablename__ = "write_off_items"

    id = db.Column(db.Integer, primary_key=True)
    write_off_id = db.Column(db.Integer, db.ForeignKey("write_offs.id"), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey("items.id"), nullable=False)
    quantity = db.Column(db.Float, nullable=False)

    item = db.relationship("Item")


# ---------------------------------------------------------------------------
# Инвентаризация (InventoryCheck)
# ---------------------------------------------------------------------------

class InventoryCheck(db.Model):
    """Сессия инвентаризации."""
    __tablename__ = "inventory_checks"

    STATUS_CHOICES = {
        "draft":     "Черновик",
        "in_progress": "Идёт счёт",
        "done":      "Завершена",
        "cancelled": "Отменена",
    }

    id = db.Column(db.Integer, primary_key=True)
    number = db.Column(db.String(32), unique=True, nullable=False)
    status = db.Column(db.String(32), nullable=False, default="draft")
    notes = db.Column(db.Text, nullable=True)

    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    finished_at = db.Column(db.DateTime, nullable=True)

    lines = db.relationship("InventoryCheckItem", backref="check", lazy="select",
                            cascade="all, delete-orphan")
    created_by = db.relationship("User", foreign_keys=[created_by_id])

    @property
    def status_label(self) -> str:
        return self.STATUS_CHOICES.get(self.status, self.status)

    @property
    def total_lines(self) -> int:
        return len(self.lines)

    @property
    def discrepancy_count(self) -> int:
        return sum(1 for l in self.lines if l.has_discrepancy)

    def __repr__(self):
        return f"<InventoryCheck {self.number} [{self.status}]>"


class InventoryCheckItem(db.Model):
    """Строка инвентаризации: учётный остаток vs фактический."""
    __tablename__ = "inventory_check_items"

    id = db.Column(db.Integer, primary_key=True)
    check_id = db.Column(db.Integer, db.ForeignKey("inventory_checks.id"), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey("items.id"), nullable=False)

    expected_qty = db.Column(db.Float, nullable=False)          # по учёту на момент старта
    actual_qty = db.Column(db.Float, nullable=True)             # фактически подсчитано
    notes = db.Column(db.String(256), nullable=True)

    item = db.relationship("Item")

    @property
    def diff(self) -> float | None:
        if self.actual_qty is None:
            return None
        return self.actual_qty - self.expected_qty

    @property
    def has_discrepancy(self) -> bool:
        d = self.diff
        return d is not None and d != 0.0