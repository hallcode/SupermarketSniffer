from database import db_engine
from sqlalchemy.orm import Session
from sqlalchemy import select
from models.brand import Brand
from models.product import Product
from models.price import Price
from scanner import Scanner

def start_scan():
    # Create database session
    with Session(db_engine) as session:
        # Get all the stuff we'll need
        select_brands = select(Brand)
        select_products = select(Product).where(Product.active == True)

        for brand_row in session.execute(select_brands):
            print(f"Starting brand: {brand_row.Brand.name}")
            scanner = Scanner(brand=brand_row.Brand, limit=3, headless=False)
            for product_row in session.execute(select_products):
                print(f" - Product: {product_row.Product.name}")
                try:
                    prices = scanner.search(product_row.Product)
                    session.add_all(prices)
                    session.commit()
                except Exception as e:
                    print(f" * Something went wrong adding {brand_row.Brand.name}/{product_row.Product.name}")
                    print(f"     > {str(e)}")

if __name__ == "__main__":
    start_scan()
