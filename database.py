from credentials import DB_HOST, DB_NAME, DB_USER, DB_PASSWORD
from psycopg2 import connect

db_connection = connect(
    dbname=DB_NAME, host=DB_HOST, user=DB_USER, password=DB_PASSWORD
)
