import uuid
from datetime import datetime


class Product:
    def __init__(
        self,
        title: str,
        id: str,
        category: str,
        search_term: str,
        unit_price: int,
        price_per_weight: int,
        weight_unit: str,
        url: str,
        seller: str
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
