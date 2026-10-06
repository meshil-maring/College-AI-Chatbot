import boto3
from botocore.client import BaseClient

from app.config import settings
from app.core.errors import AppError


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


def download_file(r2: BaseClient, bucket: str, object_key: str) -> bytes:
    """Download an R2 object and return its raw bytes."""
    response = r2.get_object(Bucket=bucket, Key=object_key)
    maximum = settings.max_upload_size_mb * 1024 * 1024
    declared = response.get("ContentLength")
    if isinstance(declared, int) and declared > maximum:
        raise AppError(
            "Stored document exceeds the configured size limit",
            status_code=422,
            code="STORAGE_OBJECT_TOO_LARGE",
        )
    data = response["Body"].read(maximum + 1)
    if len(data) > maximum:
        raise AppError(
            "Stored document exceeds the configured size limit",
            status_code=422,
            code="STORAGE_OBJECT_TOO_LARGE",
        )
    return data
