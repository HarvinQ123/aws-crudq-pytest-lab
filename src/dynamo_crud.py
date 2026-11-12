"""CRUDQ on Amazon DynamoDB with boto3 (resource API).

Table "Orders": partition key customer_id, sort key order_id,
plus a global secondary index (GSI) on status.
"""
from decimal import Decimal

import boto3
from boto3.dynamodb.conditions import Attr, Key
from botocore.exceptions import ClientError

REGION = "us-west-2"


class AlreadyExists(Exception):
    pass


class NotFound(Exception):
    pass


def dynamodb_resource(region=REGION):
    return boto3.resource("dynamodb", region_name=region)


def create_orders_table(ddb, name="Orders"):
    table = ddb.create_table(
        TableName=name,
        KeySchema=[
            {"AttributeName": "customer_id", "KeyType": "HASH"},   # partition key
            {"AttributeName": "order_id", "KeyType": "RANGE"},     # sort key
        ],
        AttributeDefinitions=[
            {"AttributeName": "customer_id", "AttributeType": "S"},
            {"AttributeName": "order_id", "AttributeType": "S"},
            {"AttributeName": "status", "AttributeType": "S"},
        ],
        GlobalSecondaryIndexes=[{
            "IndexName": "status-index",
            "KeySchema": [{"AttributeName": "status", "KeyType": "HASH"}],
            "Projection": {"ProjectionType": "ALL"},
        }],
        BillingMode="PAY_PER_REQUEST",
    )
    table.wait_until_exists()
    return table


def create_order(table, customer_id, order_id, total, status="NEW"):
    """Create. Fails if the order already exists (no silent overwrite)."""
    item = {"customer_id": customer_id, "order_id": order_id,
            "total": Decimal(str(total)), "status": status}
    try:
        table.put_item(Item=item,
                       ConditionExpression="attribute_not_exists(order_id)")
    except ClientError as err:
        if err.response["Error"]["Code"] == "ConditionalCheckFailedException":
            raise AlreadyExists(f"{customer_id}/{order_id}") from err
        raise
    return item


def get_order(table, customer_id, order_id):
    """Read by full primary key. Returns None if missing."""
    resp = table.get_item(Key={"customer_id": customer_id, "order_id": order_id})
    return resp.get("Item")


def update_status(table, customer_id, order_id, new_status):
    """Update one attribute in place; fails if the order doesn't exist."""
    try:
        resp = table.update_item(
            Key={"customer_id": customer_id, "order_id": order_id},
            UpdateExpression="SET #s = :s",
            ConditionExpression="attribute_exists(order_id)",
            ExpressionAttributeNames={"#s": "status"},   # 'status' is a reserved word
            ExpressionAttributeValues={":s": new_status},
            ReturnValues="ALL_NEW",
        )
    except ClientError as err:
        if err.response["Error"]["Code"] == "ConditionalCheckFailedException":
            raise NotFound(f"{customer_id}/{order_id}") from err
        raise
    return resp["Attributes"]


def delete_order(table, customer_id, order_id):
    """Delete. Returns the deleted item, or None if nothing was there."""
    resp = table.delete_item(Key={"customer_id": customer_id, "order_id": order_id},
                             ReturnValues="ALL_OLD")
    return resp.get("Attributes")


def query_customer_orders(table, customer_id, start=None, end=None):
    """Query: one customer's orders, optionally a sort-key range, all pages."""
    cond = Key("customer_id").eq(customer_id)
    if start and end:
        cond = cond & Key("order_id").between(start, end)
    kwargs = {"KeyConditionExpression": cond}
    items = []
    while True:
        resp = table.query(**kwargs)
        items.extend(resp["Items"])
        if "LastEvaluatedKey" not in resp:
            return items
        kwargs["ExclusiveStartKey"] = resp["LastEvaluatedKey"]


def query_by_status(table, status):
    """Query a GSI: every order with a given status, across customers."""
    resp = table.query(IndexName="status-index",
                       KeyConditionExpression=Key("status").eq(status))
    return resp["Items"]


def scan_orders_over(table, amount):
    """Scan + filter: reads the WHOLE table, then filters. Fine in tests,
    expensive on big tables. Prefer Query when you know the key."""
    kwargs = {"FilterExpression": Attr("total").gt(Decimal(str(amount)))}
    items = []
    while True:
        resp = table.scan(**kwargs)
        items.extend(resp["Items"])
        if "LastEvaluatedKey" not in resp:
            return items
        kwargs["ExclusiveStartKey"] = resp["LastEvaluatedKey"]
