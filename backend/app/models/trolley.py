from .core.database import Database
from .product import Product
from .lineitem import LineItem

class Trolley:
    def __init__(self, db: Database, accountID: int):
        self.lineItems = db.get_trolley(accountID)

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
            for lineItemID in self.lineItems:
                if newQuantity <= 0:
                    db.remove_from_trolley(accountID, lineItem.lineItemId)
                else:
                    lineItem.quantity = newQuantity
                return True 
            return False
        
        def totalCost(self):
            return sum(lineItem.priceAtPurchase for lineItem in self.LineItems)
        
        def getLineItems(self):
            return