from database import Base
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, func, ForeignKey
from typing import Optional, List


class Group(Base):
    __tablename__ = "groups"

    code: Mapped[str] = mapped_column(String(10), primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    image_url: Mapped[Optional[str]] = mapped_column(String(1024))
    colour: Mapped[Optional[str]] = mapped_column(String(8))

    products: Mapped[List["Product"]] = relationship(back_populates="group")


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    group_code: Mapped[str] = mapped_column(String(10), ForeignKey("groups.code"))
    search_term: Mapped[str] = mapped_column(String(200))
    active: Mapped[bool]
    is_food: Mapped[bool]

    group: Mapped["Group"] = relationship(back_populates="products")
    prices: Mapped[List["Price"]] = relationship(back_populates="product")
