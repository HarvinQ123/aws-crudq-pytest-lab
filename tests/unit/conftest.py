import os

import boto3
import pytest
from moto import mock_aws

from src import dynamo_crud, s3_crud

REGION = "us-west-2"


@pytest.fixture(autouse=True)
def fake_aws_credentials(monkeypatch):
    """Fake keys so a unit test can NEVER reach a real AWS account."""
    for name in ("AWS_PROFILE", "AWS_DEFAULT_PROFILE"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_SESSION_TOKEN", "testing")
    monkeypatch.setenv("AWS_DEFAULT_REGION", REGION)


@pytest.fixture
def aws():
    """Every boto3 call inside this fixture's scope hits moto, not AWS."""
    with mock_aws():
        yield


@pytest.fixture
def s3(aws):
    client = s3_crud.s3_client(REGION)
    s3_crud.create_bucket(client, "test-bucket", REGION)
    return client


@pytest.fixture
def orders_table(aws):
    return dynamo_crud.create_orders_table(dynamo_crud.dynamodb_resource(REGION))


@pytest.fixture
def seeded_table(orders_table):
    """Arrange: a known data set for Query/Scan tests."""
    rows = [("C1", "ORD-001", 20, "NEW"), ("C1", "ORD-002", 150, "SHIPPED"),
            ("C1", "ORD-003", 75, "NEW"), ("C2", "ORD-001", 300, "NEW")]
    for cust, oid, total, status in rows:
        dynamo_crud.create_order(orders_table, cust, oid, total, status)
    return orders_table


@pytest.fixture
def lambda_env(monkeypatch, s3, orders_table):
    monkeypatch.setenv("TABLE_NAME", "Orders")
    monkeypatch.setenv("BUCKET_NAME", "test-bucket")
    monkeypatch.setenv("AWS_REGION", REGION)
    return {"s3": s3, "table": orders_table}
