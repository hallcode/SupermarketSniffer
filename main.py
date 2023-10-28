from brands import brands
from product import search_categories
from scanner import scan
from playwright.sync_api import sync_playwright


def start_scan():
    with sync_playwright() as p:
        browser = p.firefox.launch(headless=False)

        for brand in brands:
            for category in search_categories:
                page = browser.new_page()
                scan(page, brand, category)
                page.close()

        browser.contexts.clear()
        browser.close()


if __name__ == "__main__":
    start_scan()
