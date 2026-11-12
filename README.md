# AWS CRUDQ + pytest lab

[![tests](https://github.com/HarvinQ123/aws-crudq-pytest-lab/actions/workflows/tests.yml/badge.svg)](https://github.com/HarvinQ123/aws-crudq-pytest-lab/actions/workflows/tests.yml)

A small Python project for testing AWS code. It does **Create, Read, Update, Delete and Query** on Amazon S3 and DynamoDB with boto3, plus a Lambda handler that ties them together. The tests run at several layers: mocked AWS (moto), scripted error responses (botocore Stubber), and opt-in tests against a real AWS account.

The unit tests need **no AWS account or credentials**. Clone, install, run.

## Quick start (macOS / Linux)

```bash
git clone https://github.com/HarvinQ123/aws-crudq-pytest-lab.git
cd aws-crudq-pytest-lab
./scripts/setup.sh          # creates .venv, installs dependencies, runs the unit tests
source .venv/bin/activate
pytest -q
```

```
30 passed, 2 skipped
```

The 2 skipped tests are the real-AWS integration tests (see [Running against real AWS](#running-against-real-aws-optional)). For step-by-step instructions, including Windows, see **Setup instructions** below.

## Setup instructions

### Prerequisites

| Need | Version | Check with |
|---|---|---|
| Python | **3.10 or newer** (CI uses 3.13) | `python3 --version` |
| git | any recent | `git --version` |
| AWS account | **not needed** for the unit tests | — |

On macOS, if `python3` is missing or older than 3.10, install it with `brew install python` or from [python.org](https://www.python.org/downloads/).

### Why a virtual environment?

A virtual environment (`.venv`) is a private folder of Python packages for this project only. Installing into it keeps this project's pinned versions of boto3, moto and pytest separate from your system Python and from your other projects. `.venv/` is in `.gitignore` and is never committed; each person creates their own.

### Step by step

**1. Get the code**

```bash
git clone https://github.com/HarvinQ123/aws-crudq-pytest-lab.git
cd aws-crudq-pytest-lab
```

**2. Create the virtual environment** (once per clone)

| macOS / Linux | Windows (PowerShell) |
|---|---|
| `python3 -m venv .venv` | `py -3 -m venv .venv` |

**3. Activate it** (every new terminal window)

| macOS / Linux | Windows (PowerShell) |
|---|---|
| `source .venv/bin/activate` | `.venv\Scripts\Activate.ps1` |

Your prompt now starts with `(.venv)`. To confirm the active Python is the project's:

| macOS / Linux | Windows (PowerShell) |
|---|---|
| `which python` → `.../aws-crudq-pytest-lab/.venv/bin/python` | `Get-Command python` → `...\.venv\Scripts\python.exe` |

If PowerShell refuses to run the activate script, run this once, then activate again:
`Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`

**4. Install the dependencies** (with the venv active)

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

`requirements.txt` pins exact versions (boto3, moto, pytest), so you get the same results as CI.

**5. Run the tests**

```bash
pytest -q                                  # everything (integration tests skip)
pytest tests/unit -v                       # unit tests, one line per test
pytest tests/unit/test_dynamo_crud.py -v   # one file
pytest -k query -v                         # tests whose name contains "query"
```

**6. When you're done**

```bash
deactivate       # leave the virtual environment (same command on every OS)
```

### One-command setup

`./scripts/setup.sh` (macOS / Linux) does steps 2, 4 and 5 for you. It checks your Python version, creates `.venv` if it doesn't exist, installs the requirements and runs the unit tests. To use a specific Python: `PYTHON=python3.13 ./scripts/setup.sh`. It can't activate the venv in your terminal (no script can), so run `source .venv/bin/activate` afterward.

### VS Code

The repo includes `.vscode/settings.json`, which points VS Code at `.venv` and turns on the pytest Test Explorer.

1. Open the folder in VS Code **after** creating `.venv`.
2. If VS Code still shows another interpreter: Command Palette (`Cmd/Ctrl+Shift+P`) → **Python: Select Interpreter** → pick `./.venv/bin/python` (Windows: `.\.venv\Scripts\python.exe`).
3. Open the Testing panel (beaker icon) to run or debug individual tests.

### Starting over

If the environment gets into a bad state, delete it and rebuild:

```bash
deactivate 2>/dev/null; rm -rf .venv     # Windows: Remove-Item -Recurse -Force .venv
./scripts/setup.sh                       # or repeat steps 2-4
```

### Troubleshooting

| Symptom | Fix |
|---|---|
| `ModuleNotFoundError: No module named 'boto3'` (or `moto`) | The venv isn't active, or step 4 was skipped. Activate it and reinstall. |
| `pytest: command not found` | Same: activate the venv. Or run `python -m pytest`. |
| `python3: command not found` / version below 3.10 | Install a newer Python (see Prerequisites). |
| `externally-managed-environment` error from pip | You're installing into the system Python. Create and activate `.venv` first. |
| VS Code: "package not installed in the selected environment" | Select the `.venv` interpreter (see VS Code above). |
| Unit tests try to reach AWS or ask for credentials | They shouldn't: `tests/unit/conftest.py` sets fake credentials. Check you're running `tests/unit` and that the `aws` fixture is in use. |

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
| `scripts/setup.sh` | One-command setup: venv, dependencies, unit tests |
| `.vscode/settings.json` | Points VS Code at `.venv` and enables the pytest Test Explorer |

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
