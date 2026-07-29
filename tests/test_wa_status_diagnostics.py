from app.modules.wa_engine.router import _safe_meta_status_diagnostics


def test_safe_meta_status_diagnostics_keeps_only_delivery_metadata():
    result = _safe_meta_status_diagnostics([
        {
            "id": "wamid.long-provider-message-id",
            "status": "failed",
            "recipient_id": "918075519571",
            "errors": [{
                "code": 131049,
                "title": "This message was not delivered",
                "error_data": {"details": "private provider detail"},
            }],
        }
    ])

    assert result == [{
        "provider_id_suffix": "vider-message-id",
        "status": "failed",
        "error_code": "131049",
        "error_title": "This message was not delivered",
    }]
    assert "recipient_id" not in result[0]
    assert "error_data" not in result[0]


def test_safe_meta_status_diagnostics_is_bounded():
    result = _safe_meta_status_diagnostics([
        {"id": str(index), "status": "sent"} for index in range(30)
    ])

    assert len(result) == 20
