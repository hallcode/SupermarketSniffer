import re
from datetime import date

from brands import Brand
from product import Category, Product
from playwright.sync_api import Page


def scan(page: Page, brand: Brand, category: Category):
    print(f"\n{brand.name} ({category.name}) ", end="")

    # Init browser page
    brand.set_page(page)

    # Dismiss cookie notice
    brand.dismiss_cookie_notice()

    # Try to find the search bar
    search_input = page.get_by_placeholder(
        re.compile("search|find|looking", re.IGNORECASE)
    )
    search_input = search_input.first
    search_input.fill(category.search_term)
    search_input.press("Enter")
    page.wait_for_load_state(brand.wait_method, timeout=180000)

    # Get product URLs
    urls = brand.get_product_urls(
        search_term=category.search_term, limit=category.limit
    )
    products = []
    for u in urls:
        try:
            # The following line does all the work
            brand.scan_product_page(u, category)
            print("#", end="")
        except Exception as e:
            # This will be running unattended on a server so, we
            # want it to just carry on come what may
            print(str(e))
            continue
