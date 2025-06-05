from ..core.database import Database
from .product import Product


class Trolley:
    def __init__(self, db: Database, accountID: int):
        self.db: Database = db
        self.accountID: int = accountID
        self.lineItems: list[dict] = db.get_trolley(accountID)

    def get_items(self):
        return self.lineItems

    def add_line_item(self, productID: int, quantity: int = 1):
        for lineItem in self.get_items():
            if lineItem["productID"] == productID:
                lineItem["quantity"] += quantity
                return self.db.change_quantity_of_product_in_trolley(
                    self.accountID, productID, lineItem["quantity"]
                )
                
        if self.db.add_to_trolley(self.accountID, productID, quantity):
            self.lineItems = self.db.get_trolley(self.accountID)
            return True
        
        return False
        

    def update_quantity(self, productID: int, newQuantity: int):
        for item in self.get_items():
            if item["productID"] == productID:
                if newQuantity <= 0:
                    self.db.remove_from_trolley(
                        self.accountID, item["lineItemID"])
                else:
                    self.db.change_quantity_of_product_in_trolley(
                        self.accountID, productID, newQuantity
                    )
                self.lineItems = self.db.get_trolley(self.accountID)
                return True
        return False

    def remove_from_trolley(self, product_id: int):
        for lineItem in self.get_items():
            if lineItem["productID"] == product_id:
                self.db.remove_from_trolley(
                    self.accountID, lineItem["lineItemID"])
                self.lineItems.remove(lineItem)
                return
        return "Failed to find"

    def clear_trolley(self):
        result = self.db.clear_trolley(self.accountID)
        self.lineItems = []
        return result
