import os

from fastapi import UploadFile
from minio import Minio

bucket_name = "images"

minio_session = Minio(
    "minio:9000",
    access_key=os.environ["MINIO_ROOT_USER"],
    secret_key=os.environ["MINIO_ROOT_PASSWORD"],
    secure=False,
)

found = minio_session.bucket_exists(bucket_name)

# Create images bucket, if not present
if not found:
    minio_session.make_bucket(bucket_name)


# mc anonymous download myminio/static


def add_image(file: UploadFile, base_url: str) -> str:
    file_name = str(hash(file))
    file_size = os.fstat(file.file.fileno()).st_size

    minio_session.put_object(
        "images",
        file_name,
        file.file,
        file_size,
        content_type=file.content_type or "application/octet-stream",
    )

    image_url = minio_session.presigned_get_object("images", file_name).removeprefix(
        "http://minio:9000/",
    )

    # prod_url = "http://prod-team-40-jpqgdebk.REDACTED"
    return base_url + image_url
