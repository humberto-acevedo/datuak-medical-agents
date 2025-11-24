import os
import pytest
from types import SimpleNamespace

import src.utils.s3_client as s3_client_module


class FakeSession:
    def __init__(self, *args, **kwargs):
        # record provided kwargs for assertions
        self.kwargs = kwargs

    def get_credentials(self):
        # Return a simple frozen-credentials like object with an access_key
        class Frozen:
            def __init__(self):
                self.access_key = 'AKIA_TEST'
                self.token = None
                self.expiry_time = None

            def get_frozen_credentials(self):
                return self

        return Frozen()

    def client(self, service_name, **kwargs):
        # Return a minimal fake s3 client implementing methods used by S3Client
        class FakeS3:
            def get_bucket_location(self, Bucket):
                return {}

            def get_bucket_encryption(self, Bucket):
                return {"Rules": []}

            def get_object(self, **kw):
                return {"Body": type("B", (), {"read": lambda self: b""})()}

            def put_object(self, **kw):
                return {}

            def head_object(self, **kw):
                raise Exception("NoSuchKey")

            def list_objects_v2(self, **kw):
                return {"Contents": []}

        return FakeS3()


def test_s3_client_prefers_profile(monkeypatch):
    # Ensure environment includes a profile
    monkeypatch.setenv('AWS_PROFILE', 'my-test-profile')

    # Patch Session used in s3_client to our fake
    monkeypatch.setattr(s3_client_module, 'Session', FakeSession)

    # Also patch config to avoid needing real config values
    fake_config = SimpleNamespace()
    fake_config.aws = SimpleNamespace(region='us-east-1', access_key_id=None, secret_access_key=None, s3_bucket='bucket', s3_endpoint_url=None)
    monkeypatch.setattr(s3_client_module, 'config', fake_config)

    # Create client - should use FakeSession and record profile_name in kwargs
    client = s3_client_module.S3Client(bucket_name='bucket')

    # Verify FakeSession was constructed with profile_name
    assert hasattr(client.session, 'kwargs')
    # We expect profile_name passed
    assert client.session.kwargs.get('profile_name') == 'my-test-profile'
    assert client.session.kwargs.get('region_name') == 'us-east-1'
