from brands.generic import Brand, NETWORK


class AsdaBrand(Brand):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.wait_method = NETWORK

    def dismiss_cookie_notice(self):
        if not self.page:
            raise Exception

        try:
            cookie_button = self.page.locator("#onetrust-accept-btn-handler")
            cookie_button.click()
            self.page.wait_for_load_state("domcontentloaded")
        except:
            pass

    def get_main_element(self):
        product_details = self.page.locator("[data-auto-id=mainProductDetails]")
        if product_details:
            try:
                product_details.first.scroll_into_view_if_needed(timeout=200)
            except:
                pass
            return product_details.first

        return self.page.get_by_role("main").or_(self.page.locator("body")).last
