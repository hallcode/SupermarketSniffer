from io import BytesIO
import boto3
from credentials import (
    AWS_ACCESS_KEY,
    AWS_SECRET_KEY,
    AWS_S3_BUCKET,
    AWS_S3_SCREENSHOT_DIR,
    AWS_S3_PUBLIC_PATH,
)


def save_file(name, file: BytesIO) -> str:
    """
    This is for saving screenshots to cloud storage nothing else.
    :param name: the name of the file, including extension
    :param file: BytesIO
    :return: String containing public URL of file
    """

    s3_client = boto3.client(
        "s3", aws_access_key_id=AWS_ACCESS_KEY, aws_secret_access_key=AWS_SECRET_KEY
    )

    filename = f"{AWS_S3_SCREENSHOT_DIR}/{name}"
    file.seek(0)
    s3_client.put_object(Body=file, Bucket=AWS_S3_BUCKET, Key=filename)

    return f"{AWS_S3_PUBLIC_PATH}/{AWS_S3_BUCKET}/{filename}"
