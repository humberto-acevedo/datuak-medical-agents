import pytest
import os
from src.utils import s3_client
from src.models.exceptions import S3Error


def test_no_credentials_raises_s3error(monkeypatch):
    """If Session.get_credentials returns None and no env creds, creation should raise S3Error."""

    class FakeSession:
        def __init__(self, *a, **kw):
            pass

        def get_credentials(self):
            return None

    # Patch the Session used in s3_client to our fake one
    monkeypatch.setattr(s3_client, "Session", FakeSession)

    # Ensure env vars are not present
    monkeypatch.delenv("AWS_ACCESS_KEY_ID", raising=False)
    monkeypatch.delenv("AWS_SECRET_ACCESS_KEY", raising=False)

    with pytest.raises(S3Error) as exc:
        s3_client.create_s3_client(bucket_name="patient-records-20251024")

    assert "No AWS credentials found" in str(exc.value)
