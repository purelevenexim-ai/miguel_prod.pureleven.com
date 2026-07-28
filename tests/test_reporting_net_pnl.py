from datetime import datetime, timezone
from types import SimpleNamespace
import unittest

from sqlalchemy.dialects import postgresql

from app.modules.reporting.service import (
    _realized_order_datetime_expr,
    _realized_order_datetime_value,
    _realized_order_month_expr,
)


def _compile_sql(expr) -> str:
    return str(
        expr.compile(
            dialect=postgresql.dialect(),
            compile_kwargs={"literal_binds": True},
        )
    ).lower()


class NetPnlRealizedDateTests(unittest.TestCase):
    def test_realized_order_datetime_expr_prefers_delivered_at(self) -> None:
        sql = _compile_sql(_realized_order_datetime_expr())
        self.assertIn("coalesce(orders.delivered_at, orders.created_at)", sql)

    def test_realized_order_month_expr_uses_realized_datetime(self) -> None:
        sql = _compile_sql(_realized_order_month_expr())
        self.assertIn(
            "to_char(coalesce(orders.delivered_at, orders.created_at), 'yyyy-mm')",
            sql,
        )

    def test_realized_order_datetime_value_prefers_delivered_at(self) -> None:
        created_at = datetime(2026, 1, 15, 10, 0, tzinfo=timezone.utc)
        delivered_at = datetime(2026, 2, 3, 18, 30, tzinfo=timezone.utc)

        order = SimpleNamespace(created_at=created_at, delivered_at=delivered_at)

        self.assertEqual(_realized_order_datetime_value(order), delivered_at)

    def test_realized_order_datetime_value_falls_back_to_created_at(self) -> None:
        created_at = datetime(2026, 1, 15, 10, 0, tzinfo=timezone.utc)

        order = SimpleNamespace(created_at=created_at, delivered_at=None)

        self.assertEqual(_realized_order_datetime_value(order), created_at)


if __name__ == "__main__":
    unittest.main()