from brands.generic import Brand

class AsdaBrand(Brand):
    def dismiss_cookie_notice(self):
        if not self.page:
            raise Exception

        try:
            cookie_button = self.page.locator("#onetrust-accept-btn-handler")
            cookie_button.click()
            self.page.wait_for_load_state("domcontentloaded")
        except:
            pass