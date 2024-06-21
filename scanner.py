import datetime
import io
import os
import re
from uuid import uuid4
from typing import List

from models.brand import Brand
from models.product import Product
from models.price import Price
from playwright.sync_api import sync_playwright, Page
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup, Tag
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from file_storage import save_file

font = ImageFont.truetype(
    font=os.path.join(os.getcwd(), "assets", "B612Mono-Regular.ttf"), size=10
)

MONEY_PATTERN = r"[0-9.]+"
UNIT_PATTERN = r"\s?(?:per|/|\s)+(each|[01aegiklmorst]+)"
PRICE_PER_POUNDS_PATTERN = rf"£({MONEY_PATTERN}){UNIT_PATTERN}"
PRICE_PER_PENNIES_PATTERN = rf"({MONEY_PATTERN})p{UNIT_PATTERN}"


class Scanner:
    def __init__(self, brand: Brand, limit: int = 3, headless: bool = False):
        self.brand = brand
        self.limit = limit
        self.prices = []
        self.current_search_term = ""

        # Initialise watermark
        self.watermark = Image.open(
            os.path.join(os.getcwd(), "assets", "LogoIcon@2x.png")
        )
        self.watermark = self.watermark.resize((41, 41))

        # Initialise browser
        self.pw = sync_playwright().start()
        self.browser = self.pw.firefox.launch(headless=headless)
        self.page = self.browser.new_page()
        self.page.goto(self.brand.start_url)
        self.brand.dismiss_cookie_notice(self.page)

    def __del__(self):
        self.browser.contexts.clear()
        self.browser.close()
        self.pw.stop()

    def search(self, product: Product) -> List[Price]:
        """
        Search for products and get their prices
        :param product:
        :return:
        """
        self.current_search_term = product.search_term

        search_input = self.page.get_by_placeholder(
            re.compile("search|find|looking", re.IGNORECASE)
        )
        search_input = search_input.first
        search_input.fill(self.current_search_term)
        search_input.press("Enter")
        self.page.wait_for_load_state(self.brand.wait_method_setting, timeout=180000)

        # Get product URLS
        prices = self.get_price_urls(product)
        for price in prices:
            self.scan_product_page(price)

        return prices

    def get_price_urls(self, product: Product):
        """
        Parse the product listing page (i.e. search results) and return
        a list of URLs for each product page.
        """
        if not self.page:
            raise Exception

        current_base_url = urlparse(self.page.url)
        self.current_search_term = product.search_term

        # This is not the same as the eponymous method - they're for different things,
        # don't be tempted to replace this line with a method call (again).
        main_by_role = self.page.get_by_role("main").or_(self.page.locator("body")).last

        bs = BeautifulSoup(main_by_role.inner_html(), "lxml")
        product_link_elements = bs.find_all(
            self.product_list_item, limit=self.limit + 3
        )

        new_prices = []
        for product_element in product_link_elements:
            if len(new_prices) >= self.limit:
                break

            link_tag = product_element.find(
                "a",
                recursive=True,
                href=re.compile("product|item", re.IGNORECASE),
            )
            if link_tag is None:
                # If we didn't find it, try another method
                link_tag = product_element.find(
                    "a",
                    recursive=True,
                    attrs={"data-oc-click": "searchProductClick"},
                )
                if link_tag is None:
                    continue

            url = urlparse(link_tag["href"])
            if url.netloc == "":
                url = urljoin(
                    current_base_url.scheme + "://" + current_base_url.netloc, url.path
                )
            else:
                url = link_tag["href"]

            new_prices.append(Price(seller=self.brand, product=product, url=url))

        return new_prices

    def scan_product_page(self, price: Price):
        self.page.goto(price.url)
        self.page.wait_for_load_state(self.brand.wait_method_setting, timeout=180000)

        price.title = self.get_product_title(price)
        price.unit_price = self.get_product_price()
        price.price_per, price.unit = self.get_product_price_weight()
        price.recorded_at = datetime.datetime.now()

        if price.unit_price == 0:
            return price

        # Detect location of images so we can blur them out later
        # This is for copywright reasons
        images = self.page.get_by_role("img").all()
        if len(images) > 0:
            self.images = []
            for img in images:
                self.images.append(img.bounding_box())

        main_element = self.get_main_element()
        try:
            main_element.scroll_into_view_if_needed(timeout=100)
        except:
            pass

        price.screenshot_url = self.screenshot_page(price)

    def get_product_price_weight(self):
        html = self.get_main_element().inner_html()
        html = re.sub(r"<!.*?->", "", html)
        bs = BeautifulSoup(html, "lxml")
        price_tag = bs.find(string=self.string_contains_price_per, recursive=True)

        price = 0
        unit = ""
        if price_tag is not None:
            text = price_tag.get_text()
            pounds_match = re.compile(PRICE_PER_POUNDS_PATTERN, re.IGNORECASE).search(
                text
            )
            if pounds_match:
                price, unit = float(pounds_match.group(1)) * 100, pounds_match.group(2)
            else:
                pennies_match = re.compile(
                    PRICE_PER_PENNIES_PATTERN, re.IGNORECASE
                ).search(text)
                if pennies_match:
                    price, unit = float(pennies_match.group(1)), pennies_match.group(2)

            # Conform units to SI units
            if unit in ("each", "Each", "EACH", "ea"):
                unit = "Ech"
            elif unit in ("l", "L", "litre", "liter", "lt", "ltr", "Ltr"):
                unit = "L"
            elif unit in ("100g", "100G", "100 grams"):
                unit = "hg"  # Hectogram (100 grams)
            elif unit in ("100ml", "100ML", "100 millilitre"):
                unit = "dL"  # Decilitre (100ml) - not to be confused with decAlitre
            elif unit in ("KG", "kg", "kilo", "kilogram", "Kilo", "Kilogram"):
                unit = "kg"
            else:
                unit = "?"

        return int(price), unit

    def get_product_title(self, price: Price):
        # Try seeing if there is a header which contains the search term
        bs = BeautifulSoup(self.get_main_element().inner_html(), "lxml")
        title_tag = bs.find(
            ["h1", "h2", "h3", "h4"], string=self.string_contains_search_terms
        )
        if title_tag is not None:
            return title_tag.get_text()

        # If not, does the URL contain the search term?
        search_term = self.current_search_term.replace(" ", "[\w\d-]*").lower()
        pattern = f"\/([\w-]*{search_term}[\w-]*)[\/-]"
        pattern = re.compile(pattern)
        path = urlparse(price.url).path
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
        pounds_pattern = re.compile(rf"£({MONEY_PATTERN})\s*$")
        pennies_pattern = re.compile(rf"({MONEY_PATTERN})p\s*$")
        bs = BeautifulSoup(self.get_main_element().inner_html(), "lxml")
        price_tag = bs.find(
            class_=re.compile("price", re.IGNORECASE), recursive=True
        ).find(string=[pounds_pattern, pennies_pattern])

        price = 0

        if price_tag is not None:
            price_text = price_tag.get_text()
            if price_text.startswith("£"):
                price = float(price_text.lstrip("£")) * 100
            if price_text.endswith("p"):
                price = float(price_text.rstrip("p"))

        return int(price)

    def get_main_element(self):
        main_by_role = self.page.get_by_role("main").or_(self.page.locator("body")).last
        return main_by_role

    def product_list_item(self, element: Tag):
        """
        Return True if the element looks like a product listing
        :param element: Tag
        :return: bool
        """
        if not self.current_search_term:
            raise Exception

        # Must be a list item
        # Or (for Aldi) some random shit
        if element.name != "li" and not element.get("data-qa") == "search-results":
            return False

        # Must contain an image
        if element.find("img", recursive=True) is None:
            return False

        # Must contain a link which includes the words product or item
        # or contains any words from the search query
        st = self.current_search_term.replace(" ", "|")
        product_link = element.find(
            "a",
            recursive=True,
            href=re.compile(rf"product|item|{st}", re.IGNORECASE),
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

    def string_contains_price_per(self, string: str):
        string = string.lstrip("(").rstrip(")")
        if (
            not string.startswith("£")
            and re.compile(rf"{MONEY_PATTERN}p", re.IGNORECASE).search(string) is None
        ):
            return False

        pounds_pattern = re.compile(PRICE_PER_POUNDS_PATTERN, re.IGNORECASE)
        if pounds_pattern.search(string):
            return True

        pennies_pattern = re.compile(PRICE_PER_PENNIES_PATTERN, re.IGNORECASE)
        if pennies_pattern.search(string):
            return True

        return False

    def screenshot_page(self, price: Price):
        image_store = io.BytesIO()
        image_store.write(self.page.screenshot(type="jpeg"))
        image_store.seek(0)

        # Stamp image
        with Image.open(image_store) as screenshot:
            # Cover images
            if self.images:
                for img in self.images:
                    if img["x"] < 0 or img["y"] < 0:
                        continue

                    if img["x"] > screenshot.width or img["y"] > screenshot.height:
                        continue

                    if img["x"] + img["width"] > screenshot.width:
                        img["width"] = screenshot.width - img["x"]

                    if img["y"] + img["height"] > screenshot.height:
                        img["height"] = screenshot.height - img["y"]

                    img_part = screenshot.crop(
                        (
                            int(img["x"]),
                            int(img["y"]),
                            int(img["x"]) + int(img["width"]),
                            int(img["y"]) + int(img["height"]),
                        )
                    )
                    img_part = img_part.filter(ImageFilter.GaussianBlur(18))
                    screenshot.paste(img_part, (int(img["x"]), int(img["y"])))

            screenshot.thumbnail((900, 750))
            screenshot.paste(self.watermark, (20, 20), mask=self.watermark)

            width, height = screenshot.width, screenshot.height
            renderer = ImageDraw.Draw(screenshot)
            renderer.rectangle(
                ((20, height - 55), (width - 20, height - 20)), fill="#FFFFFF"
            )
            renderer.text(
                (25, height - 40),
                price.url,
                anchor="ls",
                fill="#000000",
                font=font,
            )

            timestamp = price.recorded_at.strftime("%d/%b/%Y (%a) %X")
            renderer.text(
                (25, height - 25),
                timestamp,
                anchor="ls",
                fill="#000000",
                font=font,
            )

            renderer.rectangle(
                ((width - 150, height - 55), (width - 20, height - 20)), fill="#d6d6d6"
            )
            price_str = price.unit_price / 100
            renderer.text(
                (width - 25, height - 40),
                f"£{price_str:.2f}",
                anchor="rs",
                fill="#000000",
                font=font,
            )

            per_price = price.price_per / 100
            renderer.text(
                (width - 25, height - 25),
                f"£{per_price:.2f} / {price.unit}",
                anchor="rs",
                fill="#000000",
                font=font,
            )

            # Save to cloud
            image_store.seek(0)
            screenshot.save(image_store, format="jpeg", quality="web_low")
            screenshot_name = str(uuid4()) + ".jpg"
            return save_file(name=screenshot_name, file=image_store)
