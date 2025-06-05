from .core.database import Database
from .trolley import Trolley

class orderManager:
    def __init__(self, accountId: int, addressId, db: Database, trolley: list):
        
        def saveOrder(self):
            result = db.create_order(accountId, addressId, trolley)
            return result 
        
        def save_invoice(self):

            return
        def save_receipt(self): 

            return