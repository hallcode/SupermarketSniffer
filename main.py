from brands import brands
from product import search_categories
from scanner import scan


def start_scan():
    for brand in brands:
        for category in search_categories:
            scan(brand, category, headless=True)


if __name__ == "__main__":
    start_scan()
