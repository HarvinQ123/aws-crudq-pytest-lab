from src import s3_crud

B = "test-bucket"


def test_create_then_read(s3):
    s3_crud.put_text(s3, B, "notes/a.txt", "hello")
    assert s3_crud.get_text(s3, B, "notes/a.txt") == "hello"


def test_update_overwrites_whole_object(s3):
    s3_crud.put_text(s3, B, "notes/a.txt", "v1")
    s3_crud.put_text(s3, B, "notes/a.txt", "v2")
    assert s3_crud.get_text(s3, B, "notes/a.txt") == "v2"


def test_delete_then_read_returns_none(s3):
    s3_crud.put_text(s3, B, "notes/a.txt", "bye")
    s3_crud.delete_key(s3, B, "notes/a.txt")
    assert s3_crud.get_text(s3, B, "notes/a.txt") is None


def test_delete_missing_key_is_not_an_error(s3):
    s3_crud.delete_key(s3, B, "never/existed.txt")   # S3 delete is idempotent


def test_read_missing_key_returns_none(s3):
    assert s3_crud.get_text(s3, B, "nope.txt") is None


def test_query_by_prefix(s3):
    for key in ("logs/1.txt", "logs/2.txt", "img/x.png"):
        s3_crud.put_text(s3, B, key, "x")
    assert sorted(s3_crud.list_keys(s3, B, prefix="logs/")) == ["logs/1.txt", "logs/2.txt"]


def test_query_follows_pagination(s3):
    # Page size 2 with 5 objects forces 3 pages; a bug that reads one page fails.
    for i in range(5):
        s3_crud.put_text(s3, B, f"p/{i}.txt", "x")
    assert len(s3_crud.list_keys(s3, B, prefix="p/", page_size=2)) == 5
