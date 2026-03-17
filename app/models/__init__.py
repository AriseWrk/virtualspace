from app.models.user import User
from app.models.warehouse import (
    Item, Category,
    StockMovement,
    Receipt, ReceiptItem,
    WriteOff, WriteOffItem,
    InventoryCheck, InventoryCheckItem,
)
from app.models.order import Order, OrderItem
from app.models.project import (
    Project, ChecklistItem, CableJournal,
    IPTable, ProjectPhoto, ProjectNote,
    ProjectDocument, ProjectOrder,
)
from app.models.pts import (
    ObjectCategory, ServiceObject, ServiceRecord,
    ObjectPassword, ObjectFile, ObjectEquipment,
)
from app.models.service_task import ServiceTask, ServiceTaskEngineer, ServiceTaskReport
from app.models.app_settings import AppSettings
from app.models.vehicle import Vehicle, VehicleTrip, VehicleRequest
from app.models.fault_record import FaultRecord
__all__ = [
    "User",
    "Item", "Category",
    "StockMovement",
    "Receipt", "ReceiptItem",
    "WriteOff", "WriteOffItem",
    "InventoryCheck", "InventoryCheckItem",
    "Order", "OrderItem",
    "Project", "ChecklistItem", "CableJournal",
    "IPTable", "ProjectPhoto", "ProjectNote",
    "ProjectDocument", "ProjectOrder",
    "ObjectCategory", "ServiceObject", "ServiceRecord",
    "ObjectPassword", "ObjectFile", "ObjectEquipment", "ServiceTask", "ServiceTaskEngineer", "ServiceTaskReport", "AppSettings",
    "Vehicle", "VehicleTrip", "VehicleRequest", "FaultRecord"
]