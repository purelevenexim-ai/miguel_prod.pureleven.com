from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ORDERS_HTML = (ROOT / "frontend" / "orders.html").read_text()
ORDERS_CSS = (ROOT / "frontend" / "styles" / "orders-modern.css").read_text()


def test_orders_design_is_scoped_and_loaded_after_global_theme():
    global_pos = ORDERS_HTML.index("/styles/shadcn-app.css")
    orders_pos = ORDERS_HTML.index("/styles/orders-modern.css")
    assert global_pos < orders_pos
    assert '<body class="orders-page">' in ORDERS_HTML
    assert ".orders-page" in ORDERS_CSS


def test_orders_has_no_active_style_elements_after_head():
    body_markup = ORDERS_HTML.split("</head>", 1)[1]
    assert "<style" not in body_markup


def test_orders_toolbar_actions_are_grouped_without_spacer():
    toolbar_start = ORDERS_HTML.index('<div class="toolbar"', ORDERS_HTML.index('id="manualOrdersPanel"'))
    toolbar_end = ORDERS_HTML.index("</div>", ORDERS_HTML.index('class="orders-toolbar-actions"', toolbar_start))
    toolbar_markup = ORDERS_HTML[toolbar_start:toolbar_end]
    assert 'class="orders-toolbar-actions"' in toolbar_markup
    assert 'class="spacer"' not in toolbar_markup


def test_orders_mobile_cards_keep_date_selection_and_actions():
    assert ".orders-page .col-checkbox" in ORDERS_CSS
    assert "position: absolute" in ORDERS_CSS
    assert ".orders-page .col-date" in ORDERS_CSS
    assert 'content: "Created "' in ORDERS_CSS
    assert ".orders-page .col-actions" in ORDERS_CSS


def test_orders_preserves_semantic_status_colours():
    assert 'class="status-sel status-${o.status}"' in ORDERS_HTML
    for status in ("confirmed", "delivered", "cancelled", "returned"):
        assert f"status-{status}" in ORDERS_CSS
