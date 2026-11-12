"""CRUDQ on Amazon S3 with boto3.

S3 is an object store: keys map to blobs. "Update" means overwrite the whole
object, and "Query" means listing keys by prefix.
"""
import boto3
from botocore.exceptions import ClientError

REGION = "us-west-2"


def s3_client(region=REGION):
    return boto3.client("s3", region_name=region)


def create_bucket(s3, bucket, region=REGION):
    # Outside us-east-1, S3 requires a LocationConstraint.
    s3.create_bucket(Bucket=bucket,
                     CreateBucketConfiguration={"LocationConstraint": region})


def put_text(s3, bucket, key, text):
    """Create, or Update by overwriting."""
    s3.put_object(Bucket=bucket, Key=key, Body=text.encode("utf-8"),
                  ContentType="text/plain")


def get_text(s3, bucket, key):
    """Read. Returns None if the key doesn't exist; re-raises other errors."""
    try:
        resp = s3.get_object(Bucket=bucket, Key=key)
    except ClientError as err:
        if err.response["Error"]["Code"] == "NoSuchKey":
            return None
        raise
    return resp["Body"].read().decode("utf-8")


def delete_key(s3, bucket, key):
    """Delete. S3 returns success even if the key was already gone."""
    s3.delete_object(Bucket=bucket, Key=key)


def list_keys(s3, bucket, prefix="", page_size=1000):
    """Query: every key under a prefix, following pagination."""
    paginator = s3.get_paginator("list_objects_v2")
    keys = []
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix,
                                   PaginationConfig={"PageSize": page_size}):
        keys.extend(obj["Key"] for obj in page.get("Contents", []))
    return keys
