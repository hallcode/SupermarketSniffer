from brands.generic import Brand, NETWORK
from brands.asda import AsdaBrand as Asda
from brands.aldi import Aldi

sainsburys = Brand("Sainsburys", "https://www.sainsburys.co.uk/")
sainsburys.wait_method = NETWORK

brands = [
    Aldi("Aldi", "https://groceries.aldi.co.uk/")
    # Asda("ASDA", "https://www.asda.com/"),
    # Brand("Tesco", "https://www.tesco.com/"),
    # sainsburys,
    # Brand("Morrisons", "https://groceries.morrisons.com/"),
]
