"""botocore Stubber: script exact AWS responses, including errors moto can't
easily produce (AccessDenied, throttling). No network and no moto."""
import boto3
import pytest
from botocore.exceptions import ClientError
from botocore.stub import Stubber

from src import s3_crud


@pytest.fixture
def stubbed_s3():
    client = boto3.client("s3", region_name="us-west-2")
    with Stubber(client) as stub:
        yield client, stub
        stub.assert_no_pending_responses()   # every scripted call was used


def test_access_denied_is_not_swallowed(stubbed_s3):
    client, stub = stubbed_s3
    stub.add_client_error("get_object", service_error_code="AccessDenied",
                          http_status_code=403,
                          expected_params={"Bucket": "b", "Key": "secret.txt"})
    with pytest.raises(ClientError) as exc:
        s3_crud.get_text(client, "b", "secret.txt")
    assert exc.value.response["Error"]["Code"] == "AccessDenied"


def test_no_such_key_becomes_none(stubbed_s3):
    client, stub = stubbed_s3
    stub.add_client_error("get_object", service_error_code="NoSuchKey", http_status_code=404)
    assert s3_crud.get_text(client, "b", "missing.txt") is None


def test_put_sends_expected_parameters(stubbed_s3):
    client, stub = stubbed_s3
    stub.add_response("put_object", {}, expected_params={
        "Bucket": "b", "Key": "k.txt", "Body": b"hi", "ContentType": "text/plain"})
    s3_crud.put_text(client, "b", "k.txt", "hi")
