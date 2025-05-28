class Trolley: 
    def __init__(self):
        self.lineItems = []

    def addLineItem(self, product):
        quantity = 1
        for lineItem in self.lineItems:
            if lineItem.product.productID == product.poroductID:
                lineItem.quantity += quantity
                return
        self.lineItems.append(lineItem(product, quantity))
    
    def UpdateQuantity(self, productID, newQuantity):
        for lineItem in self.lineItems:
            if newQuantity <= 0:
                self.lineItems.remove(lineItem)
            else:
                lineItem.quantity = newQuantity
            return True 
        return False
    
    def totalCost(self):
        return sum(lineItem.price for lineItem in self.LineItems)
    
    def getLineItems(self):
        return