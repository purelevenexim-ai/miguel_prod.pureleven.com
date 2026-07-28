from __future__ import annotations

import json
import logging
from datetime import date, datetime, timedelta, timezone
from typing import Any
from urllib.parse import quote

import httpx

logger = logging.getLogger(__name__)


class IndiaPostPortalClient:
    """Client for the India Post customer self-service portal booking report."""

    BASE_URL = "https://app.indiapost.gov.in/customer-selfservice"
    CSRF_URL = f"{BASE_URL}/api/auth/csrf"
    LOGIN_URL = f"{BASE_URL}/api/auth/callback/customerlogin"
    BOOKING_REPORT_URL = f"{BASE_URL}/reports/booking-report"
    BOOKING_REPORT_ACTION_ID = "7fc46ae01cec65993c68c6db2df30defd598c9126a"
    BOOKING_REPORT_ROUTER_STATE = [
        "",
        {
            "children": [
                "(controller)",
                {
                    "children": [
                        "reports",
                        {
                            "children": [
                                "booking-report",
                                {
                                    "children": [
                                        "__PAGE__",
                                        {},
                                        None,
                                        None,
                                    ]
                                },
                                None,
                                None,
                            ]
                        },
                        None,
                        None,
                    ]
                },
                None,
                None,
            ]
        },
        None,
        None,
        True,
    ]

    def __init__(self, user_id: str, password: str):
        self.user_id = str(user_id or "").strip()
        self.password = password or ""

    @classmethod
    def _router_state_header(cls) -> str:
        payload = json.dumps(cls.BOOKING_REPORT_ROUTER_STATE, separators=(",", ":"))
        return quote(payload, safe="")

    @staticmethod
    def _format_report_date(value: date) -> str:
        return value.strftime("%d-%m-%Y")

    def _booking_report_query(
        self,
        *,
        from_date: date,
        to_date: date,
        skip: int = 0,
        limit: int = 0,
        payment_mode_code: str | None = None,
        contract_id: str | int | None = None,
    ) -> str:
        params = [
            f"start-date={self._format_report_date(from_date)}",
            f"end-date={self._format_report_date(to_date)}",
            f"customer-id={self.user_id}",
            f"skip={max(skip, 0)}",
            f"limit={max(limit, 0)}",
        ]
        if payment_mode_code:
            params.append(f"payment-mode-code={payment_mode_code}")
        if contract_id not in (None, ""):
            params.append(f"contract_id={contract_id}")
        return "?" + "&".join(params)

    async def _login(self, client: httpx.AsyncClient) -> None:
        if not self.user_id or not self.password:
            raise RuntimeError("India Post portal user ID/password are not configured")

        csrf_resp = await client.get(self.CSRF_URL)
        csrf_resp.raise_for_status()
        csrf_token = csrf_resp.json().get("csrfToken")
        if not csrf_token:
            raise RuntimeError("India Post portal did not return a CSRF token")

        login_resp = await client.post(
            self.LOGIN_URL,
            data={
                "csrfToken": csrf_token,
                "userId": self.user_id,
                "password": self.password,
                "callbackUrl": "/home",
                "json": "true",
                "redirect": "false",
            },
            headers={
                "Origin": "https://app.indiapost.gov.in",
                "Referer": f"{self.BASE_URL}/login",
                "Content-Type": "application/x-www-form-urlencoded",
            },
        )
        if login_resp.status_code not in (200, 302, 303):
            raise RuntimeError(f"India Post portal login failed: HTTP {login_resp.status_code}")

        session_tokens = [key for key in client.cookies.keys() if "session-token" in key.lower()]
        if not session_tokens:
            raise RuntimeError("India Post portal login did not establish a session")

    @staticmethod
    def _extract_action_result(payload: str) -> dict[str, Any]:
        rows: dict[str, str] = {}
        for line in payload.splitlines():
            key, sep, value = line.partition(":")
            if not sep or not key:
                continue
            rows[key] = value

        bootstrap = json.loads(rows.get("0", "{}"))
        action_ref = bootstrap.get("a")
        if isinstance(action_ref, str) and action_ref.startswith("$@"):
            action_row_id = action_ref[2:]
        elif isinstance(action_ref, str) and action_ref.startswith("$"):
            action_row_id = action_ref[1:]
        else:
            action_row_id = "1"

        action_payload = rows.get(action_row_id)
        if not action_payload:
            raise RuntimeError("India Post portal booking report returned an unexpected action payload")

        result = json.loads(action_payload)
        if not isinstance(result, dict):
            return {"success": True, "data": result}

        data = result.get("data")
        if isinstance(data, list):
            result["data"] = [
                {**row, "_source": "portal_booking_report"} if isinstance(row, dict) else row
                for row in data
            ]
        result.setdefault("success", True)
        return result

    async def fetch_booking_report(
        self,
        *,
        from_date: date,
        to_date: date,
        skip: int = 0,
        limit: int = 0,
        payment_mode_code: str | None = None,
        contract_id: str | int | None = None,
    ) -> dict[str, Any]:
        query = self._booking_report_query(
            from_date=from_date,
            to_date=to_date,
            skip=skip,
            limit=limit,
            payment_mode_code=payment_mode_code,
            contract_id=contract_id,
        )
        body = json.dumps(["ARTICLE_BOOKING_REPORT_MIS", "GET", None, query], separators=(",", ":"))

        async with httpx.AsyncClient(timeout=45.0, follow_redirects=False) as client:
            try:
                await self._login(client)
                resp = await client.post(
                    self.BOOKING_REPORT_URL,
                    content=body,
                    headers={
                        "Accept": "text/x-component",
                        "Next-Action": self.BOOKING_REPORT_ACTION_ID,
                        "Next-Router-State-Tree": self._router_state_header(),
                        "Origin": "https://app.indiapost.gov.in",
                        "Referer": self.BOOKING_REPORT_URL,
                        "Content-Type": "text/plain;charset=UTF-8",
                    },
                )
                if resp.status_code != 200:
                    return {"success": False, "error": f"HTTP {resp.status_code}: {resp.text[:300]}"}

                content_type = (resp.headers.get("content-type") or "").lower()
                if not content_type.startswith("text/x-component"):
                    return {"success": False, "error": f"Unexpected content type: {content_type or 'unknown'}"}

                return self._extract_action_result(resp.text)
            except Exception as exc:
                logger.error("India Post portal booking report error: %s", exc)
                return {"success": False, "error": str(exc)}

    async def fetch_recent_booking_report(self, days: int = 7) -> dict[str, Any]:
        to_date = datetime.now(timezone.utc).date()
        from_date = to_date - timedelta(days=max(days, 1))
        return await self.fetch_booking_report(from_date=from_date, to_date=to_date, limit=0)