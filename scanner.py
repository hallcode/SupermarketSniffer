import re
from datetime import date

from brands import Brand
from product import Category, Product
from playwright.sync_api import Page


def scan(page: Page, brand: Brand, category: Category):
    print("Starting " + brand.name)

    # Init browser page
    brand.set_page(page)

    # Dismiss cookie notice
    brand.dismiss_cookie_notice()

    # Try to find the search bar
    search_input = page.get_by_placeholder(re.compile("search|find", re.IGNORECASE))
    search_input = search_input.first
    search_input.fill(category.search_term)
    search_input.press("Enter")
    page.wait_for_load_state("networkidle")

    # Get product URLs
    urls = brand.get_product_urls(search_term=category.search_term)
    products = []
    for u in urls:
        # The following line does all the work
        brand.scan_product_page(u, category)
