from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend"
NAV_MODULE = FRONTEND / "modules" / "mobile-nav.v4.js"
APP_STYLES = FRONTEND / "styles" / "shadcn-app.css"

TENANT_PAGES = [
    "customer-retarget.html",
    "customers.html",
    "gst.html",
    "invoices.html",
    "label-editor.html",
    "lead-messages.html",
    "leads.html",
    "marketing.html",
    "orders.html",
    "products.html",
    "profit-loss.html",
    "tenant-admin.html",
    "vendors.html",
    "whatsapp.html",
]


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_every_authenticated_tenant_page_loads_the_same_navigation_module():
    expected = '<script src="/modules/mobile-nav.v4.js?v=20260728c"></script>'

    for page in TENANT_PAGES:
        assert expected in read(FRONTEND / page), page


def test_every_page_uses_the_same_canonical_navigation_styles():
    expected = '<link rel="stylesheet" href="/styles/shadcn-app.css?v=20260728b">'

    for page in FRONTEND.glob("*.html"):
        assert expected in read(page), page.name


def test_canonical_schema_contains_the_complete_tenant_navigation():
    source = read(NAV_MODULE)
    expected_destinations = [
        "/tenant-admin.html",
        "/tenant-admin.html?section=employees",
        "/tenant-admin.html?section=reports",
        "/profit-loss.html",
        "/leads.html",
        "/customers.html",
        "/orders.html",
        "/invoices.html",
        "/products.html",
        "/products.html?view=inventory",
        "/vendors.html",
        "/gst.html",
        "/marketing.html",
        "/customer-retarget.html",
        "/whatsapp.html",
        "/tenant-admin.html?section=shipping-config",
        "/label-editor.html",
    ]

    for destination in expected_destinations:
        assert destination in source

    assert "aside.innerHTML = ''" in source
    assert "data-canonical-nav" in source
    assert "canonical-nav-ready" in source
    assert "itemIsActive" in source
    assert "activateTenantSection" in source


def test_platform_admin_keeps_its_separate_navigation_context():
    source = read(NAV_MODULE)

    assert "currentPath === '/platform-admin.html'" in source
    assert "currentPath === '/platform-login.html'" in source


def test_canonical_sidebar_has_shared_visual_contract():
    styles = read(APP_STYLES)

    assert ".canonical-sidebar {" in styles
    assert ".canonical-sidebar nav a.active" in styles
    assert ".canonical-sidebar .sidebar-footer" in styles
    assert ".canonical-nav-icon" in styles
    assert "body.canonical-nav-ready" in styles


def test_tenant_dashboard_supports_normalized_sidebar_replacement():
    source = read(FRONTEND / "tenant-admin.html")

    assert "document.getElementById('nav-empName')" in source
    assert "document.getElementById('nav-empEmail')" in source
    assert "document.getElementById('nav-empRole')" in source
    assert "document.querySelectorAll('#sideNav a')" in source
