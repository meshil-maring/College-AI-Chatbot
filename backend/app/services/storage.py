import boto3
from botocore.client import BaseClient

from app.config import settings


def _r2_endpoint() -> str:
    endpoint = settings.r2_endpoint_url.rstrip("/")
    bucket = settings.r2_bucket
    if endpoint.endswith(f"/{bucket}"):
        endpoint = endpoint[: -len(f"/{bucket}")]
    return endpoint


def get_r2_client() -> BaseClient:
    return boto3.client(
        "s3",
        endpoint_url=_r2_endpoint(),
        aws_access_key_id=settings.r2_access_key_id,
        aws_secret_access_key=settings.r2_secret_access_key,
        region_name="auto",
    )


def upload_file(r2: BaseClient, bucket: str, object_key: str, data: bytes, mime_type: str) -> str:
    """Upload bytes to R2 and return the object key."""
    r2.put_object(
        Bucket=bucket,
        Key=object_key,
        Body=data,
        ContentType=mime_type,
    )
    return object_key


def delete_file(r2: BaseClient, bucket: str, object_key: str) -> None:
    """Best-effort deletion of an R2 object. Errors are suppressed."""
    try:
        r2.delete_object(Bucket=bucket, Key=object_key)
    except Exception:
        pass
