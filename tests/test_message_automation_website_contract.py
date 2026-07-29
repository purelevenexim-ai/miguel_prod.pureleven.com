from pathlib import Path


SERVICE_SOURCE = (
    Path(__file__).resolve().parents[1]
    / "backend/app/modules/message_automation/service.py"
).read_text()


def test_customer_facing_website_default_is_pureleven():
    assert '"website_url": "https://www.pureleven.com"' in SERVICE_SOURCE
    assert 'website_url = "https://www.pureleven.com"' in SERVICE_SOURCE
    assert "https://purelevenexim.com" not in SERVICE_SOURCE


def test_internal_myshopify_domain_is_not_used_as_public_website():
    assert 'if ".myshopify.com" not in store_website_url.lower()' in SERVICE_SOURCE
