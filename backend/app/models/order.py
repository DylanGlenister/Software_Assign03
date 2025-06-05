from .core.database import Database
from .trolley import Trolley

class orderManager:
    def __init__(self, accountId: int, addressId, db: Database, trolley: list):
        
        def saveOrder(self):
            orderId = db.create_order(accountId, addressId, trolley)
            return orderId
        
        def save_invoice(self, orderId):
            result = db.save_invoice(accountId, orderId)
            return result 
        def save_receipt(self, orderId):
            result = db.save_receipt(accountId, orderId)
            return result 