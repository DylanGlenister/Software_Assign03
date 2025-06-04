from .core.database import Database
from .product import Product
from .lineitem import LineItem

class Trolley:
    def __init__(self, db: Database, accountID: int):
        self.lineItems = []

    def addLineItem(self, productID):
        quantity = 1
        for lineItem in self.lineItems:
            if lineItem.productID == productID:
                lineItem.quantity += quantity
                return
        self.lineItems.append(lineItem(productID, quantity))
        return
    
    def UpdateQuantity(self, lineItem: LineItem, newQuantity: int):
        for lineItem in self.lineItems:
            if newQuantity <= 0:
                self.lineItems.remove(lineItem)
            else:
                lineItem.quantity = newQuantity
            return True 
        return False
    
    def totalCost(self):
        return sum(lineItem.priceAtPurchase for lineItem in self.LineItems)
    
    def getLineItems(self):
        return