from ..core.database import Database
from .trolley import Trolley


class orderManager:
    def __init__(self, accountId: int, addressId, db: Database, trolley: list):
        self.accountId: int = accountId
        self.addressId: int = addressId
        self.trolley: list = trolley
        self.db: Database = db

    def createorder(self):
        orderId = self.db.create_order(
            self.accountId, self.addressId, self.trolley)
        return orderId

    def save_invoice(self, orderId):
        result = self.db.save_invoice(self.accountId, orderId)
        return result

    def save_receipt(self, orderId):
        result = self.db.save_receipt(self.accountId, orderId)
        return result
