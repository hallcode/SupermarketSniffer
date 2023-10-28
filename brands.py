import os.path
import re
from playwright.sync_api import Page
from bs4 import BeautifulSoup, Tag
from urllib.parse import urlparse, urljoin
import os.path
from datetime import date
from product import Category

class Brand:
    # This class contains all the functionality and _should_ work on each
    # website, however there are some things which need specific targeting
    # in which case the class can be extended and methods overridden to
    # make it work.

    def __init__(self, name: str, start_url):
        self.name = name
        self.start_url = start_url

    def set_page(self, page: Page):
        self.page = page
        page.goto(self.start_url)

    def dismiss_cookie_notice(self):
        if not self.page:
            raise Exception

        try:
            cookie_button = self.page.get_by_role("button").filter(
                has_text=re.compile("allow|accept", re.IGNORECASE)
            )
            cookie_button.wait_for()
            cookie_button = cookie_button.first
            cookie_button.hover()
            cookie_button.click()
            self.page.wait_for_load_state("domcontentloaded")
        except:
            # If there's no cookie notice... we don't care
            pass

    def get_product_urls(self, search_term: str, limit=5):
        # Parse the product listing page (i.e. search results) and return
        # a list of URLs for each product page.
        if not self.page:
            raise Exception

        current_base_url = urlparse(self.page.url)

        links = []
        bs = BeautifulSoup(self.page.inner_html("body"), "lxml")
        self.current_search_term = search_term
        products = bs.find_all(self.product_list_item, limit=limit*2)

        for p in products:
            if len(links) >= limit:
                break

            link_tag = p.find(
                "a",
                recursive=True,
                attrs={"href": re.compile("product|item", re.IGNORECASE)},
            )
            if link_tag is None:
                continue

            link = urlparse(link_tag["href"])
            if link.netloc == '':
                link = urljoin(
                    current_base_url.scheme + '://' + current_base_url.netloc, link.path
                )

            if link in links:
                continue

            links.append(str(link))

        return links

    def product_list_item(self, element: Tag):
        """
        Return True if the element looks like a product listing
        :param element: Tag
        :return: bool
        """
        if not self.current_search_term:
            raise Exception

        # Must be a list item
        if element.name != "li":
            return False

        # Must contain an image
        if element.find("img", recursive=True) is None:
            return False

        # Must contain a link which includes the words product or item
        product_link = element.find(
            "a",
            recursive=True,
            attrs={"href": re.compile("product|item", re.IGNORECASE)},
        )
        if product_link is None:
            return False

        # Must NOT contain the words 'Offer' or 'Sponsored'
        offer_text = element.find(
            recursive=True, string=re.compile("offer|sponsored", re.IGNORECASE)
        )
        if offer_text is not None:
            return False

        # Must contain the search term somewhere in the text
        search_text_element = element.find(
            recursive=True,
            string=re.compile(self.current_search_term, re.IGNORECASE),
        )
        if search_text_element is None:
            return False

        return True

    def scan_product_page(self, product_url: str, category: Category):
        output_path = os.path.join(os.getcwd(), "output", date.today().isoformat(), self.name)
        if not os.path.exists(output_path):
            os.makedirs(output_path)

        self.page.goto(product_url)
        self.page.wait_for_load_state('networkidle')

        screenshot_name = self.page.title().replace(' ', '_').lower() + ".png"
        self.page.screenshot(path=os.path.join(output_path, screenshot_name))


class Asda(Brand):
    def dismiss_cookie_notice(self):
        if not self.page:
            raise Exception

        try:
            cookie_button = self.page.locator("#onetrust-accept-btn-handler")
            cookie_button.click()
            self.page.wait_for_load_state("domcontentloaded")
        except:
            pass


brands = [
    Brand("Tesco", "https://www.tesco.com/"),
    # Brand("Sainsburys", "https://www.sainsburys.co.uk/"),
    # Brand("Morrisons", "https://groceries.morrisons.com/"),
    Asda("ASDA", "https://www.asda.com/"),
]
