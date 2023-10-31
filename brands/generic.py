import base64
import io
import os
import re
import tempfile

from playwright.sync_api import Page
from bs4 import BeautifulSoup, Tag
from urllib.parse import urlparse, urljoin
from datetime import date, datetime
from product import Category, Product
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from file_storage import save_file

font = ImageFont.truetype(
    font=os.path.join(os.getcwd(), "assets", "B612Mono-Regular.ttf"), size=10
)

MONEY_PATTERN = r"[0-9.]+"
UNIT_PATTERN = r"\s?(?:per|/|\s)+(each|[01aegiklmorst]+)"
PRICE_PER_POUNDS_PATTERN = rf"£({MONEY_PATTERN}){UNIT_PATTERN}"
PRICE_PER_PENNIES_PATTERN = rf"({MONEY_PATTERN})p{UNIT_PATTERN}"

DOM = "domcontentloaded"
NETWORK = "networkidle"


class Brand:
    # This class contains all the functionality and _should_ work on each
    # website, however there are some things which need specific targeting
    # in which case the class can be extended and methods overridden to
    # make it work.

    def __init__(self, name: str, start_url, seller_id=0):
        self.current_search_term = None
        self.screenshot_url = None
        self.name = name
        self.start_url = start_url
        self.wait_method = DOM
        self.watermark = Image.open(
            os.path.join(os.getcwd(), "assets", "LogoIcon@2x.png")
        )
        self.watermark = self.watermark.resize((41, 41))
        self.seller_id = seller_id

    def __del__(self):
        self.watermark.close()

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
        main_by_role = self.page.get_by_role("main").or_(self.page.locator("body")).last
        bs = BeautifulSoup(main_by_role.inner_html(), "lxml")
        self.current_search_term = search_term
        products = bs.find_all(self.product_list_item, limit=limit * 2)

        for p in products:
            if len(links) >= limit:
                break

            link_tag = p.find(
                "a",
                recursive=True,
                href=re.compile("product|item", re.IGNORECASE),
            )
            if link_tag is None:
                # If we didn't find it, try another method
                link_tag = p.find(
                    "a",
                    recursive=True,
                    attrs={"data-oc-click": "searchProductClick"},
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

    def get_main_element(self):
        main_by_role = self.page.get_by_role("main").or_(self.page.locator("body")).last
        if main_by_role:
            main_by_role.scroll_into_view_if_needed()
            return main_by_role

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

    def scan_product_page(self, product_url: str, category: Category):
        self.page.goto(product_url)
        self.current_search_term = category.search_term
        self.page.wait_for_load_state(self.wait_method, timeout=180000)

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

        # Detect location of images so we can blur them out later
        # This is for copywright reasons
        images = self.page.get_by_role("img").all()
        if len(images) > 0:
            self.images = []
            for img in images:
                self.images.append(img.bounding_box())

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
        pounds_pattern = re.compile(rf"£({MONEY_PATTERN})\s*$")
        pennies_pattern = re.compile(rf"({MONEY_PATTERN})p\s*$")
        bs = BeautifulSoup(self.get_main_element().inner_html(), "lxml")
        price_tag = bs.find(
            class_=re.compile("price", re.IGNORECASE), recursive=True
        ).find(string=[pounds_pattern, pennies_pattern])

        price = 0

        if price_tag is not None:
            price_text = price_tag.get_text()
            try:
                self.page.locator(
                    price_tag.parent.name, has_text=price_text
                ).first.scroll_into_view_if_needed()
            except:
                pass

            if price_text.startswith("£"):
                price = float(price_text.lstrip("£")) * 100
            if price_text.endswith("p"):
                price = float(price_text.rstrip("p"))

        return price

    def get_product_price_weight(self):
        self.page.wait_for_load_state(DOM)
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
                unit = ""
            elif unit in ("l", "L", "litre", "liter", "lt", "ltr", "Ltr"):
                unit = "L"
            elif unit in ("100g", "100G", "100 grams"):
                unit = "hg"  # Hectogram (100 grams)
            elif unit in ("100ml", "100ML", "100 millilitre"):
                unit = "dL"  # Decilitre (100ml) - not to be confused with decAlitre
            elif unit in ("KG", "kg", "kilo", "kilogram", "Kilo", "Kilogram"):
                unit = "kg"

        return int(price), unit

    def screenshot_page(self, product: Product):
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
                product.url,
                anchor="ls",
                fill="#000000",
                font=font,
            )

            timestamp = datetime.fromtimestamp(product.timestamp).strftime(
                "%d/%b/%Y (%a) %X"
            )
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
            price = product.unit_price / 100
            renderer.text(
                (width - 25, height - 40),
                f"£{price:.2f}",
                anchor="rs",
                fill="#000000",
                font=font,
            )

            per_price = product.price_per_weight / 100
            renderer.text(
                (width - 25, height - 25),
                f"£{per_price:.2f} / {product.weight_unit}",
                anchor="rs",
                fill="#000000",
                font=font,
            )

            # Save to azure
            image_store.seek(0)
            screenshot.save(image_store, format="jpeg", quality="web_low")
            screenshot_name = str(product.uuid) + ".jpg"
            self.screenshot_url = save_file(name=screenshot_name, file=image_store)
