import os.path
import re
from datetime import date

from brands import Brand
from product import Category, Product


def scan(page, brand: Brand, category: Category):
    print("Starting " + brand.name)

    output_path = os.path.join(os.getcwd(), "output", date.today().isoformat())
    if not os.path.exists(output_path):
        os.makedirs(output_path)

    page.goto(brand.start_url)

    # Dismiss cookie notice
    try:
        cookie_button = page.get_by_role("button").get_by_text(
            re.compile("allow|accept", re.IGNORECASE)
        )
        cookie_button.wait_for()
        cookie_button = cookie_button.first
        cookie_button.hover()
        cookie_button.click()
        page.wait_for_load_state("domcontentloaded")
    except:
        # If there's no cookie notice... we don't care
        pass

    # Try to find the search bar
    search_input = page.get_by_placeholder(re.compile("search|find", re.IGNORECASE))
    search_input = search_input.first
    search_input.fill(category.search_term)
    search_input.press("Enter")
    page.wait_for_load_state("networkidle")

    screenshot_name = brand.name.lower() + "_" + category.name.lower() + ".png"
    page.screenshot(path=os.path.join(output_path, screenshot_name))
