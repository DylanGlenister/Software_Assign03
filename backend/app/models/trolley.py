from ..core.database import Database
from .product import Product

class Trolley:
    def __init__(self, db: Database, accountID: int):
        self.lineItems = db.get_trolley(accountID)

        def getTrolley():
            self.lineItems = db.get_trolley(accountID)
            return 

        def addLineItem(self, productID):
            quantity = 1
            for lineItem in self.lineItems:
                if lineItem["productID"] == productID:
                    lineItem["quantity"] += quantity
                    db.change_quantity_of_product_in_trolley(accountID, productID, quantity)
                    return
            db.add_to_trolley(accountID, productID, quantity)
            return
        
        def UpdateQuantity(self, productID: int, newQuantity: int):
            for lineItem in self.lineItems:
                if newQuantity <= 0:
                    db.remove_from_trolley(accountID, self.lineItem.lineItemId)
                else:
                    db.change_quantity_of_product_in_trolley(accountID, productID, newQuantity)
                return True 
            return False
        
        def remove_from_trolley(self, db: Database, product_id: int):
            return db.remove_from_trolley(self.accountID, product_id)
        
        def clear_trolley(self, db: Database):
            return db.clear_trolley(self.accountID)