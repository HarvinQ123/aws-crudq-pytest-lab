# AWS CRUDQ + pytest lab

[![tests](https://github.com/HarvinQ123/aws-crudq-pytest-lab/actions/workflows/tests.yml/badge.svg)](https://github.com/HarvinQ123/aws-crudq-pytest-lab/actions/workflows/tests.yml)

A small Python project for testing AWS code. It does **Create, Read, Update, Delete and Query** on Amazon S3 and DynamoDB with boto3, plus a Lambda handler that ties them together. The tests run at several layers: mocked AWS (moto), scripted error responses (botocore Stubber), and opt-in tests against a real AWS account.

The unit tests need **no AWS account or credentials**. Clone, install, run.

## Quick start

```bash
git clone https://github.com/HarvinQ123/aws-crudq-pytest-lab.git
cd aws-crudq-pytest-lab
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pytest -q
```

```
30 passed, 2 skipped
```

The 2 skipped tests are the real-AWS integration tests (see below).

## What's inside

| Path | What it does |
|---|---|
| `src/s3_crud.py` | S3: put, get, overwrite, delete, list by prefix with pagination |
| `src/dynamo_crud.py` | DynamoDB `Orders` table (partition key + sort key + GSI): conditional create, get, update, delete, Query, GSI Query, Scan |
| `src/handler.py` | Lambda handler: validates a POST body, writes an order to DynamoDB and a receipt to S3, returns 201 / 400 / 409 |
| `tests/unit/conftest.py` | pytest fixtures: fake credentials, `mock_aws`, ready-made bucket and table, seeded data |
| `tests/unit/` | 30 unit tests (moto + botocore Stubber) |
| `tests/integration/` | 2 real-AWS tests with unique resource names and guaranteed cleanup (opt-in) |
| `buildspec.yml` | AWS CodeBuild config that runs the suite inside AWS and publishes a JUnit report |
| `.github/workflows/tests.yml` | GitHub Actions: runs the unit tests on every push |

## CRUDQ at a glance

| Operation | S3 | DynamoDB |
|---|---|---|
| Create | `put_object` | `put_item` + `attribute_not_exists` (no silent overwrite) |
| Read | `get_object` (`NoSuchKey` → `None`) | `get_item` |
| Update | `put_object` again (replaces the whole object) | `update_item` + `attribute_exists` (no accidental upsert) |
| Delete | `delete_object` (idempotent) | `delete_item` with `ReturnValues=ALL_OLD` |
| Query | `list_objects_v2` by prefix, paginated | `query` on the partition key / sort-key range, or on a GSI, paginated |

## Testing approach

| Layer | Tool | Used for |
|---|---|---|
| Mocked AWS | [moto](https://github.com/getmoto/moto) `mock_aws` | CRUD logic, conditions, pagination, the Lambda handler end to end |
| Scripted responses | botocore `Stubber` | Error paths moto can't easily produce (AccessDenied); asserting exact request parameters |
| Real AWS (opt-in) | pytest + boto3 | IAM, eventual consistency and anything else a mock can't show |

Design choices that make the code testable:

- **Dependency injection.** Functions take the boto3 client as a parameter, so the same code runs against moto, a Stubber or real AWS.
- **Safe by default.** An autouse fixture sets fake credentials and clears `AWS_PROFILE`, so a unit test can't reach a real account.
- **Clients created after the mock starts.** The Lambda handler creates its clients per call, not at import time.
- **Side effects are verified.** Tests read back from DynamoDB and S3 instead of trusting return values.
- **Negative cases.** Duplicate creates, updates to missing records, bad input (parametrized), and a forced multi-page listing.

To see how data moves through the fixtures for any test:

```bash
pytest tests/unit/test_handler.py::test_happy_path_writes_dynamo_and_s3 --setup-show
```

## Running against real AWS (optional)

Use a **sandbox account** with a least-privilege role. Never use production credentials.

```bash
RUN_AWS_INTEGRATION=1 pytest tests/integration -v
```

Each test creates `crudq-it-<random>` resources and deletes them in fixture teardown, even when a test fails. The role needs S3 and DynamoDB permissions scoped to `crudq-it-*`. In AWS CodeBuild, `buildspec.yml` runs both suites using the project's service role, so no keys are stored.

> Status: the unit suite runs in CI on every push. The integration tests and `buildspec.yml` haven't been run against a live account yet.

## Tech

Python 3.13 · boto3 · pytest · moto · botocore Stubber · GitHub Actions · AWS CodeBuild
