from decimal import Decimal

import pytest

from src import dynamo_crud as d


# ---- Create / Read ----------------------------------------------------------
def test_create_then_get(orders_table):
    d.create_order(orders_table, "C1", "ORD-001", 19.99)
    item = d.get_order(orders_table, "C1", "ORD-001")
    assert item["status"] == "NEW"
    assert item["total"] == Decimal("19.99")      # numbers come back as Decimal


def test_create_duplicate_is_rejected(orders_table):
    d.create_order(orders_table, "C1", "ORD-001", 10)
    with pytest.raises(d.AlreadyExists):
        d.create_order(orders_table, "C1", "ORD-001", 99)
    assert d.get_order(orders_table, "C1", "ORD-001")["total"] == 10   # not overwritten


def test_get_missing_returns_none(orders_table):
    assert d.get_order(orders_table, "C9", "ORD-404") is None


# ---- Update -----------------------------------------------------------------
def test_update_status_returns_new_values(orders_table):
    d.create_order(orders_table, "C1", "ORD-001", 10)
    updated = d.update_status(orders_table, "C1", "ORD-001", "SHIPPED")
    assert updated["status"] == "SHIPPED"
    assert d.get_order(orders_table, "C1", "ORD-001")["status"] == "SHIPPED"


def test_update_missing_order_raises_not_found(orders_table):
    with pytest.raises(d.NotFound):
        d.update_status(orders_table, "C1", "ORD-404", "SHIPPED")
    assert d.get_order(orders_table, "C1", "ORD-404") is None   # no ghost row created


# ---- Delete -----------------------------------------------------------------
def test_delete_returns_old_item_then_gone(orders_table):
    d.create_order(orders_table, "C1", "ORD-001", 10)
    old = d.delete_order(orders_table, "C1", "ORD-001")
    assert old["order_id"] == "ORD-001"
    assert d.get_order(orders_table, "C1", "ORD-001") is None


def test_delete_missing_returns_none(orders_table):
    assert d.delete_order(orders_table, "C1", "ORD-404") is None


# ---- Query ------------------------------------------------------------------
def test_query_returns_only_that_customer_sorted(seeded_table):
    ids = [i["order_id"] for i in d.query_customer_orders(seeded_table, "C1")]
    assert ids == ["ORD-001", "ORD-002", "ORD-003"]   # sorted by sort key


def test_query_sort_key_range(seeded_table):
    items = d.query_customer_orders(seeded_table, "C1", "ORD-002", "ORD-003")
    assert [i["order_id"] for i in items] == ["ORD-002", "ORD-003"]


@pytest.mark.parametrize("status,expected", [
    ("NEW", {("C1", "ORD-001"), ("C1", "ORD-003"), ("C2", "ORD-001")}),
    ("SHIPPED", {("C1", "ORD-002")}),
    ("CANCELLED", set()),
])
def test_query_gsi_by_status(seeded_table, status, expected):
    got = {(i["customer_id"], i["order_id"]) for i in d.query_by_status(seeded_table, status)}
    assert got == expected


def test_scan_with_filter(seeded_table):
    got = {(i["customer_id"], i["order_id"]) for i in d.scan_orders_over(seeded_table, 100)}
    assert got == {("C1", "ORD-002"), ("C2", "ORD-001")}
