from database import Base
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, func, ForeignKey, Text
from typing import Optional, List
from datetime import datetime


class Price(Base):
    __tablename__ = "prices"

    id: Mapped[int] = mapped_column(primary_key=True)
    seller_id: Mapped[int] = mapped_column(ForeignKey("brands.id"))
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    title: Mapped[str] = mapped_column(Text)
    recorded_at: Mapped[datetime] = mapped_column(insert_default=func.now())
    unit_price: Mapped[int]
    price_per: Mapped[int]
    unit: Mapped[str] = mapped_column(String(3))
    screenshot_url: Mapped[Optional[str]] = mapped_column(String(1024))
    url: Mapped[str] = mapped_column(String(1024))

    product: Mapped["Product"] = relationship(back_populates="prices")
    seller: Mapped["Brand"] = relationship(back_populates="prices")
