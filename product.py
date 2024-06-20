import math
import sys
import uuid
from datetime import datetime

import psycopg2

from database import db_connection
from psycopg2 import sql


class Category:
    def __init__(self, code: str, group_code: str, search_term: str, limit: int = 5):
        self.code = code
        self.group_code = group_code
        self.search_term = search_term
        self.limit = limit

    @staticmethod
    def get_all() -> list:
        with db_connection.cursor() as conn:
            categories = []

            query = sql.SQL(
                """SELECT {code}, {group}, {q}, {limit} from {table}
                   JOIN {groups} ON {group} = {group_key}"""
            ).format(
                code=sql.Identifier("categories", "id"),
                group=sql.Identifier("categories", "group_id"),
                q=sql.Identifier("categories", "search_terms"),
                limit=sql.Identifier("groups", "limit"),
                table=sql.Identifier("categories"),
                groups=sql.Identifier("groups"),
                group_key=sql.Identifier("groups", "id"),
            )

            conn.execute(query)

            while True:
                row = conn.fetchone()
                if row is None:
                    break

                search_terms = str(row[2]).split(";")
                for term in search_terms:
                    limit = math.floor(row[3] / len(search_terms))
                    if limit < 1:
                        limit = 1
                    categories.append(
                        Category(
                            code=row[0],
                            group_code=row[1],
                            search_term=term,
                            limit=limit,
                        )
                    )

        return categories


class Product:
    def __init__(
        self,
        title: str,
        id: str,
        category: Category,
        unit_price: int,
        price_per_weight: int,
        weight_unit: str,
        url: str,
        seller,
    ):
        self.id = id
        self.title = title
        self.category = category
        self.unit_price = unit_price
        self.price_per_weight = price_per_weight
        self.weight_unit = weight_unit
        self.url = url
        self.seller = seller
        self.screenshot_url = None
        self.uuid = uuid.uuid4()

        today = datetime.now()
        self.timestamp = today.timestamp()

    def save(self):
        with db_connection.cursor() as conn:
            if Product.exists(self.url):
                return

            insert = sql.SQL(
                """INSERT INTO {table} VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )"""
            ).format(table=sql.Identifier("products"))
            try:
                conn.execute(
                    insert,
                    (
                        str(self.uuid),
                        self.id,
                        self.seller.seller_id,
                        self.category.group_code,
                        self.category.code,
                        self.title,
                        self.unit_price,
                        self.price_per_weight,
                        self.weight_unit,
                        self.url,
                        self.screenshot_url,
                        datetime.fromtimestamp(self.timestamp),
                    ),
                )
                db_connection.commit()
            except psycopg2.Error as e:
                print(f"\n**********\nDB Error: {str(e)}**********\n")

    @staticmethod
    def exists(product_url):
        with db_connection.cursor() as conn:
            # First check there isn't already a product with the same date and URL
            select_dups = sql.SQL(
                """SELECT count(*) FROM {table}
                WHERE {url} = %s AND {timestamp} >= now()::date
            """
            ).format(
                table=sql.Identifier("products"),
                url=sql.Identifier("url"),
                timestamp=sql.Identifier("timestamp"),
            )
            conn.execute(select_dups, (product_url,))
            return conn.fetchone()[0] > 0
