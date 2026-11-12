"""A small AWS Lambda handler: POST an order -> DynamoDB row + S3 receipt.

Testing idea: a Lambda handler is just a Python function. Call it with a fake
event dict, with moto standing in for DynamoDB and S3.
"""
import json
import os

import boto3

from src import dynamo_crud, s3_crud

REQUIRED = ("customer_id", "order_id", "total")


def _resources():
    # Created per call (not at import) so tests can start moto first.
    region = os.environ.get("AWS_REGION", "us-west-2")
    table = boto3.resource("dynamodb", region_name=region).Table(os.environ["TABLE_NAME"])
    s3 = boto3.client("s3", region_name=region)
    return table, s3, os.environ["BUCKET_NAME"]


def _response(code, body):
    return {"statusCode": code, "headers": {"Content-Type": "application/json"},
            "body": json.dumps(body)}


def lambda_handler(event, context):
    try:
        data = json.loads(event.get("body") or "")
    except json.JSONDecodeError:
        return _response(400, {"error": "body must be JSON"})

    missing = [f for f in REQUIRED if f not in data]
    if missing:
        return _response(400, {"error": f"missing fields: {', '.join(missing)}"})
    if not isinstance(data["total"], (int, float)) or data["total"] <= 0:
        return _response(400, {"error": "total must be a positive number"})

    table, s3, bucket = _resources()
    try:
        dynamo_crud.create_order(table, data["customer_id"], data["order_id"], data["total"])
    except dynamo_crud.AlreadyExists:
        return _response(409, {"error": "order already exists"})

    key = f"receipts/{data['customer_id']}/{data['order_id']}.txt"
    s3_crud.put_text(s3, bucket, key, f"Order {data['order_id']} total {data['total']}")
    return _response(201, {"order_id": data["order_id"], "receipt_key": key})
