from io import BytesIO

import boto3
import pandas as pd
import pytest
from botocore.response import StreamingBody
from botocore.stub import Stubber

from src.storage import CloudStorage, csv_bytes


def test_s3_contract_with_stub(monkeypatch):
    monkeypatch.setenv("BUCKET_NAME", "test-car-data")
    monkeypatch.setenv("S3_PREFIX", "portfolio/cars")
    client = boto3.client(
        "s3",
        region_name="us-east-1",
        aws_access_key_id="fixture",
        aws_secret_access_key="fixture",
    )
    frame = pd.DataFrame({"Preço": [30_990.00]})
    data = csv_bytes(frame)
    with Stubber(client) as stub:
        stub.add_response(
            "put_object",
            {},
            {
                "Bucket": "test-car-data",
                "Key": "portfolio/cars/test.csv",
                "Body": data,
                "ContentType": "text/csv; charset=utf-8",
            },
        )
        stub.add_response(
            "get_object",
            {"Body": StreamingBody(BytesIO(data), len(data))},
            {"Bucket": "test-car-data", "Key": "portfolio/cars/test.csv"},
        )
        storage = CloudStorage(ambiente="PROD", s3_client=client)
        storage.salvar(frame, "test.csv")
        pd.testing.assert_frame_equal(storage.ler_csv("test.csv"), frame)
        stub.assert_no_pending_responses()


@pytest.mark.parametrize("key", ["../private.csv", "/etc/passwd", "a//b", "a\\b", "a\nb"])
def test_rejects_unsafe_storage_keys(tmp_path, key):
    storage = CloudStorage(ambiente="LOCAL", local_path=tmp_path)
    with pytest.raises(ValueError, match="Invalid storage key"):
        storage.write_bytes(key, b"value", "text/plain")


def test_fails_for_typo_in_storage_mode():
    with pytest.raises(ValueError, match="AMBIENTE"):
        CloudStorage(ambiente="PORD")
