from database import Base
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, func
from typing import Optional, List
import re
from playwright.sync_api import Page

DOM = "domcontentloaded"
NETWORK = "networkidle"


class Brand(Base):
    # This class contains all the functionality and _should_ work on each
    # website, however there are some things which need specific targeting
    # in which case the class can be extended and methods overridden to
    # make it work.

    __tablename__ = "brands"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    start_url: Mapped[str] = mapped_column(String(1024))
    wait_method: Mapped[str] = mapped_column(String(10))
    class_name: Mapped[str] = mapped_column(String(100))
    logo_url: Mapped[Optional[str]] = mapped_column(String(100))
    colour_code: Mapped[Optional[str]] = mapped_column(String(10))

    prices: Mapped[List["Price"]] = relationship(back_populates="seller")

    @property
    def wait_method_setting(self):
        if self.wait_method == "NETWORK":
            return NETWORK

        return DOM

    def dismiss_cookie_notice(self, page: Page):
        try:
            cookie_button = page.get_by_role("button").filter(
                has_text=re.compile("allow|accept", re.IGNORECASE)
            )
            cookie_button.wait_for()
            cookie_button = cookie_button.first
            cookie_button.hover()
            cookie_button.click()
            page.wait_for_load_state("domcontentloaded")
        except:
            # If there's no cookie notice... we don't care
            pass
