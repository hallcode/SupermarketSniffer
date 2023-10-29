import os
import re
from playwright.sync_api import Page
from bs4 import BeautifulSoup, Tag
from urllib.parse import urlparse, urljoin
from datetime import date, datetime
from product import Category, Product
from PIL import Image, ImageDraw, ImageFont
from csv import csv

font = ImageFont.truetype(
    font=os.path.join(os.getcwd(), "assets", "B612Mono-Regular.ttf"), size=10
)


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
        products = bs.find_all(self.product_list_item, limit=limit * 2)

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
            if link.netloc == "":
                link = urljoin(
                    current_base_url.scheme + "://" + current_base_url.netloc, link.path
                )
            else:
                link = link_tag["href"]

            if link in links:
                continue

            links.append(link)

        return links

    def string_contains_search_terms(self, string: str):
        try:
            terms = self.current_search_term.lower().split(" ")
            string = string.lower()
            for term in terms:
                if term not in string:
                    return False

            return True
        except AttributeError:
            return False

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

        # Must contain the search term(s) somewhere in the text
        search_text_element = element.find(
            recursive=True,
            string=self.string_contains_search_terms,
        )
        if search_text_element is None:
            return False

        return True

    def scan_product_page(self, product_url: str, category: Category):
        self.page.goto(product_url)
        self.current_search_term = category.search_term
        self.page.wait_for_load_state("networkidle")

        # Create product object
        price_per, unit = self.get_product_price_weight()
        product = Product(
            title=self.get_product_title(product_url),
            id=self.get_product_id(product_url),
            category=category,
            unit_price=int(self.get_product_price()),
            price_per_weight=price_per,
            weight_unit=unit,
            url=product_url,
            seller=self.name,
        )

        if product.unit_price == 0:
            return product

        csv.add_line(product)
        self.screenshot_page(product)

        return product

    def get_product_id(self, product_url: str = ""):
        # See if we can get the ID from the URL
        # It's probably a string of numbers
        url = urlparse(product_url)
        id = re.search(re.compile("\d{4,}[\d-]*"), url.path)
        if id:
            return id.group()

        return ""

    def get_product_title(self, product_url: str = ""):
        # Try seeing if there is a header which contains the search term
        bs = BeautifulSoup(self.page.inner_html("body"), "lxml")
        title_tag = bs.find(['h1', 'h2', 'h3', 'h4'], string=self.string_contains_search_terms)
        if title_tag is not None:
            return title_tag.get_text()

        # If not, does the URL contain the search term?
        search_term = self.current_search_term.replace(" ", "[\w\d-]*").lower()
        pattern = f"\/([\w-]*{search_term}[\w-]*)[\/-]"
        pattern = re.compile(pattern)
        path = urlparse(product_url).path
        match = re.search(pattern, path)
        if match:
            try:
                return match.group(1).replace("-", " ").title()
            except:
                pass

        return self.page.title()

    def get_product_price(self):
        """
        Get the package price from the product page
        :return: the price of one unit IN PENCE
        """
        pounds_pattern = re.compile('£(\d+\.\d+)\s*$')
        pennies_pattern = re.compile('(\d+[.\d]+)p\s*$')
        bs = BeautifulSoup(self.page.inner_html("body"), "lxml")
        price_tag = bs.find(class_=re.compile("price"), recursive=True).find(
            string=[pounds_pattern, pennies_pattern]
        )

        price = 0

        if price_tag is not None:
            price_text = price_tag.get_text()
            if price_text.startswith('£'):
                price = float(price_text.lstrip('£')) * 100
            if price_text.endswith('p'):
                price = float(price_text.rstrip('p'))

        return price

    def get_product_price_weight(self):
        pattern = re.compile('£(\d+\.\d+)\s?(?:per|\/)?\s?(each|[0-9]*[kgmltrie]+)')

        return 0, "each"

    def screenshot_page(self, product: Product):
        output_path = os.path.join(
            os.getcwd(), "output", date.today().isoformat()
        )
        if not os.path.exists(output_path):
            os.makedirs(output_path)

        screenshot_name = str(product.uuid) + ".png"
        screenshot_path = os.path.join(output_path, screenshot_name)
        self.page.screenshot(path=screenshot_path)

        # Stamp image
        with Image.open(screenshot_path) as screenshot:
            screenshot.thumbnail((900, 750))
            width, height = screenshot.width, screenshot.height
            renderer = ImageDraw.Draw(screenshot)
            renderer.rectangle(
                ((20, height - 55), (width - 20, height - 20)), fill="#FFFFFF"
            )
            renderer.text(
                (25, height - 40),
                product.url,
                anchor="ls",
                fill="#000000",
                font=font,
            )

            timestamp = datetime.fromtimestamp(product.timestamp).strftime('(%a) %x @ %X')
            renderer.text(
                (25, height - 25),
                timestamp,
                anchor="ls",
                fill="#000000",
                font=font,
            )

            renderer.rectangle(
                ((width-100, height - 55), (width - 20, height - 20)), fill="#d6d6d6"
            )
            price = product.unit_price/100
            renderer.text(
                (width-25, height - 40),
                f"£{price:.2f}",
                anchor="rs",
                fill="#000000",
                font=font,
            )
            screenshot.save(screenshot_path)
