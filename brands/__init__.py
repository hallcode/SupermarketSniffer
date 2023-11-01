from brands.generic import Brand, NETWORK
from brands.asda import AsdaBrand as Asda
from brands.aldi import Aldi

sainsburys = Brand("Sainsburys", "https://www.sainsburys.co.uk/", seller_id=7)
sainsburys.wait_method = NETWORK

# The IDs are hard coded here and in the database.
# I know this is bad, but it's quicker to code.
brands = [
    Aldi("Aldi", "https://groceries.aldi.co.uk/", seller_id=4),
    Asda("ASDA", "https://www.asda.com/", seller_id=5),
    Brand("Morrisons", "https://groceries.morrisons.com/", seller_id=6),
    sainsburys,
    Brand("Tesco", "https://www.tesco.com/", seller_id=3),
]
