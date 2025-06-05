from ..core.database import Database
from .trolley import Trolley


class OrderManager:
    def __init__(self, accountId: int, addressId:int, db: Database):
        self.accountId: int = accountId
        self.addressId: int = addressId
        self.trolley: Trolley = Trolley(db, accountId)
        self.orders: list = []
        self.db: Database = db

    def create_order(self) -> int:
        orderId = self.db.create_order(
            self.accountId, self.addressId)
        return orderId

    def save_invoice(self, orderId):
        result = self.db.save_invoice(self.accountId, orderId)
        return result

    def save_receipt(self, orderId):
        result = self.db.save_receipt(self.accountId, orderId)
        return result

    def get_orders(self):
        self.orders = self.db.get_orders_from_account(self.accountId)
        return self.orders
