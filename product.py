import uuid
from datetime import datetime


class Category:
    def __init__(self, name: str, search_term: str, product_type: str):
        self.name = name
        self.search_term = search_term
        self.product_type = product_type


class Product:
    def __init__(
        self,
        title: str,
        id: str,
        category: Category,
        search_term: str,
        unit_price: int,
        price_per_weight: int,
        weight_unit: str,
        url: str,
        seller: str,
    ):
        self.id = id
        self.title = title
        self.category = category
        self.search_term = search_term
        self.unit_price = unit_price
        self.price_per_weight = price_per_weight
        self.weight_unit = weight_unit
        self.url = url
        self.seller = seller

        new_uuid = uuid.uuid4()
        self.uuid = str(new_uuid)

        today = datetime.now()
        self.timestamp = today.timestamp()


search_categories = [Category("Milk", "skimmed milk", "Dairy")]
