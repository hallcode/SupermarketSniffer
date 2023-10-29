from datetime import date
import os
from product import Product


class CsvOutput:
    def __init__(self):
        output_path = os.path.join(os.getcwd(), "output", date.today().isoformat())
        if not os.path.exists(output_path):
            os.makedirs(output_path)

        self.file = open(
            os.path.join(output_path, date.today().isoformat() + ".csv"), "w"
        )

        self.file.write(
            '"uuid","id","seller","category","product","title","price","price_per","unit","url","timestamp"\n'
        )

    def __del__(self):
        self.close()

    def close(self):
        if self.file:
            self.file.close()

    def add_line(self, product: Product):
        self.file.write(f'"{product.uuid}",')
        self.file.write(f'"{product.id}",')
        self.file.write(f'"{product.seller}",')
        self.file.write(f'"{product.category.product_type}",')
        self.file.write(f'"{product.category.name}",')
        self.file.write(f'"{product.title}",')
        self.file.write(f"{product.unit_price},")
        self.file.write(f"{product.price_per_weight},")
        self.file.write(f'"{product.weight_unit}",')
        self.file.write(f'"{product.url}",')
        self.file.write(f"{product.timestamp}")
        self.file.write("\n")
