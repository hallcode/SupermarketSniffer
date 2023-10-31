from io import BytesIO
import os
from tempfile import NamedTemporaryFile
from azure.storage.blob import BlobServiceClient
from credentials import CONNECTION_STRING, CONTAINER

client = BlobServiceClient.from_connection_string(conn_str=CONNECTION_STRING)


def save_file(name, file: BytesIO):
    new_image = client.get_blob_client(CONTAINER, name)
    file.seek(0)

    new_image.upload_blob(file.read())
    return new_image.url
