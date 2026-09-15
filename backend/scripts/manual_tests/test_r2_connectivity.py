"""
Temporary R2 connectivity test.
Run from the backend directory: python scripts/manual_tests/test_r2_connectivity.py
(Settings load .env relative to the working directory, so run it from backend/.)
"""
import os
import sys

# Resolve the backend package root so the script runs from any working directory.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from app.config import settings
from app.services.storage import get_r2_client


def main() -> None:
    bucket = settings.r2_bucket
    print(f"Testing R2 connectivity for bucket: {bucket}")

    try:
        r2 = get_r2_client()
        response = r2.list_objects_v2(Bucket=bucket, MaxKeys=1)
    except Exception as exc:
        print(f"FAIL — could not reach bucket: {exc}")
        sys.exit(1)

    status = response.get("ResponseMetadata", {}).get("HTTPStatusCode")
    count = response.get("KeyCount", 0)
    print(f"OK — HTTP {status}, objects visible (up to 1 sampled): {count}")


if __name__ == "__main__":
    main()
