from .core.database import Database

class LineItem: 
    def __init__(self, productId: int, quanity: int, db: Database, priceAtPurchase: float):

        self.productID = productId
        self.quanity = quanity
        self.priceAtPurchase = priceAtPurchase