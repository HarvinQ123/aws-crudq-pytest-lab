import json

import pytest

from src import dynamo_crud, s3_crud
from src.handler import lambda_handler


def make_event(body):
    """Minimal API Gateway-style event: only the fields the handler reads."""
    return {"httpMethod": "POST", "body": body if isinstance(body, str) else json.dumps(body)}


def test_happy_path_writes_dynamo_and_s3(lambda_env):
    resp = lambda_handler(make_event({"customer_id": "C1", "order_id": "ORD-9", "total": 42}), None)

    assert resp["statusCode"] == 201
    body = json.loads(resp["body"])
    assert body["receipt_key"] == "receipts/C1/ORD-9.txt"
    # Verify side effects, not just the return value.
    assert dynamo_crud.get_order(lambda_env["table"], "C1", "ORD-9")["total"] == 42
    assert s3_crud.get_text(lambda_env["s3"], "test-bucket", body["receipt_key"]) == "Order ORD-9 total 42"


def test_duplicate_order_returns_409(lambda_env):
    event = make_event({"customer_id": "C1", "order_id": "ORD-9", "total": 42})
    assert lambda_handler(event, None)["statusCode"] == 201
    assert lambda_handler(event, None)["statusCode"] == 409


@pytest.mark.parametrize("body,fragment", [
    ("not json", "must be JSON"),
    ("", "must be JSON"),
    ({"order_id": "ORD-9", "total": 5}, "customer_id"),
    ({"customer_id": "C1", "order_id": "ORD-9", "total": 0}, "positive"),
    ({"customer_id": "C1", "order_id": "ORD-9", "total": "5"}, "positive"),
])
def test_bad_input_returns_400_and_writes_nothing(lambda_env, body, fragment):
    resp = lambda_handler(make_event(body), None)
    assert resp["statusCode"] == 400
    assert fragment in json.loads(resp["body"])["error"]
    assert s3_crud.list_keys(lambda_env["s3"], "test-bucket") == []
