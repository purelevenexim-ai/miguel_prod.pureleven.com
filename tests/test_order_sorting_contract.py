from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SERVICE = (ROOT / "backend" / "app" / "modules" / "orders" / "service.py").read_text()


def test_return_priority_uses_status_history_not_general_updated_at():
    assert "OrderStatusHistory.new_status == OrderStatus.returned" in SERVICE
    assert "returned_activity_at = func.coalesce(returned_at, Order.created_at)" in SERVICE
    assert "returned_activity_at >= today_start" in SERVICE
    assert "func.coalesce(Order.updated_at, Order.created_at) >= today_start" not in SERVICE


def test_returns_older_than_thirty_days_receive_archive_rank():
    assert "thirty_days = now_utc - timedelta(days=30)" in SERVICE
    assert "aged_return_rank = case(" in SERVICE
    assert "Order.created_at < thirty_days" in SERVICE
    assert "aged_return_rank.asc()" in SERVICE


def test_order_pagination_has_stable_id_tie_breaker():
    assert "Order.created_at.desc()," in SERVICE
    assert "Order.id.desc()," in SERVICE
