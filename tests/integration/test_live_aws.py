"""Integration tests against a REAL AWS account. Skipped unless RUN_AWS_INTEGRATION=1.

They create uniquely named resources, tag nothing shared, and always clean up.
Run in a sandbox account with a least-privilege role, never in production.
"""
import os
import uuid

import boto3
import pytest

from src import dynamo_crud, s3_crud

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(os.environ.get("RUN_AWS_INTEGRATION") != "1",
                       reason="set RUN_AWS_INTEGRATION=1 to hit real AWS"),
]
REGION = os.environ.get("AWS_REGION", "us-west-2")


@pytest.fixture
def live_bucket():
    s3 = boto3.client("s3", region_name=REGION)
    name = f"crudq-it-{uuid.uuid4().hex[:12]}"
    s3_crud.create_bucket(s3, name, REGION)
    yield s3, name
    for key in s3_crud.list_keys(s3, name):          # teardown runs even on failure
        s3.delete_object(Bucket=name, Key=key)
    s3.delete_bucket(Bucket=name)


@pytest.fixture
def live_table():
    ddb = boto3.resource("dynamodb", region_name=REGION)
    table = dynamo_crud.create_orders_table(ddb, name=f"crudq-it-{uuid.uuid4().hex[:8]}")
    yield table
    table.delete()


def test_s3_round_trip(live_bucket):
    s3, name = live_bucket
    s3_crud.put_text(s3, name, "it/a.txt", "live")
    assert s3_crud.get_text(s3, name, "it/a.txt") == "live"
    assert s3_crud.list_keys(s3, name, "it/") == ["it/a.txt"]


def test_dynamo_round_trip(live_table):
    dynamo_crud.create_order(live_table, "C1", "ORD-1", 10)
    assert dynamo_crud.update_status(live_table, "C1", "ORD-1", "SHIPPED")["status"] == "SHIPPED"
    assert len(dynamo_crud.query_customer_orders(live_table, "C1")) == 1
    assert dynamo_crud.delete_order(live_table, "C1", "ORD-1") is not None
