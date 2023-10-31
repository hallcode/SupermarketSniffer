from brands import brands
from product import search_categories
from scanner import scan
from playwright.sync_api import sync_playwright
import csv


def start_scan():
    with sync_playwright() as p:
        browser = p.firefox.launch(headless=False)

        for brand in brands:
            for category in search_categories:
                try:
                    page = browser.new_page()
                    scan(page, brand, category)
                    page.close()
                except:
                    # This will be running unattended on a server so, we
                    # want it to just carry on come what may
                    print(
                        f' ** Error scanning for "{category.search_term}" at {brand.name}'
                    )
                    continue

        browser.contexts.clear()
        browser.close()


if __name__ == "__main__":
    start_scan()
