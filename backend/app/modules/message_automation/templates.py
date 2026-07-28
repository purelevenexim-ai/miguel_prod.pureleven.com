from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True)
class AutomationTemplate:
    key: str
    channel: str
    title: str
    category: str
    subject: str | None
    body: str
    meta_template_name: str | None = None
    meta_category: str | None = None
    language: str = "en"


TEMPLATES: Dict[str, AutomationTemplate] = {
    "order_created": AutomationTemplate(
        key="order_created",
        channel="whatsapp",
        title="Order Created",
        category="utility",
        subject=None,
        meta_template_name="pureleven_prod_order",
        meta_category="UTILITY",
        body=(
            "Hi {{customer_name}}, your Pureleven order *{{order_number}}* is confirmed.\n\n"
            "Items: {{items_summary}}\n"
            "Order value: INR {{total_amount}}\n\n"
            "We are preparing it carefully and will share tracking as soon as dispatch is booked.\n"
            "Website: {{website_url}}\n\n"
            "Reply STOP if you do not want automated order updates."
        ),
    ),
    "tracking_added": AutomationTemplate(
        key="tracking_added",
        channel="whatsapp",
        title="Tracking Added",
        category="utility",
        subject=None,
        meta_template_name="pureleven_tracking_update",
        meta_category="UTILITY",
        body=(
            "Hi {{customer_name}}, your Pureleven order *{{order_number}}* has been dispatched.\n\n"
            "Courier: {{courier_name}}\n"
            "Tracking: *{{tracking_number}}*\n"
            "Current status: {{status_text}}\n"
            "Current location: {{location}}\n"
            "Expected delivery: {{expected_delivery}}\n\n"
            "We will keep checking the shipment and update you if there is any important movement."
        ),
    ),
    "tracking_update_3day": AutomationTemplate(
        key="tracking_update_3day",
        channel="whatsapp",
        title="3-Day Tracking Update with Status",
        category="utility",
        subject=None,
        meta_template_name="pureleven_tracking_update_3day",
        meta_category="UTILITY",
        body=(
            "Hi {{customer_name}}, here is the latest update for Pureleven order *{{order_number}}*.\n\n"
            "Courier: {{courier_name}}\n"
            "Tracking: *{{tracking_number}}*\n"
            "Current status: {{status_text}}\n"
            "Current location: {{location}}\n"
            "Expected delivery: {{expected_delivery}}\n\n"
            "Reply with any delivery concerns. We're here to help!\n"
            "{{whatsapp_link}}"
        ),
    ),
    "review_request": AutomationTemplate(
        key="review_request",
        channel="whatsapp",
        title="Review Request - 15 Days After Delivery",
        category="marketing",
        subject=None,
        meta_template_name="pureleven_review_request",
        meta_category="MARKETING",
        body=(
            "Hi {{customer_name}}, 15 days after your order - how was it?\n\n"
            "Share your Pureleven experience with a Google review:\n"
            "{{google_review_url}}\n\n"
            "Your honest feedback helps us:\n"
            "✓ Improve product quality\n"
            "✓ Enhance our service\n"
            "✓ Help other customers decide\n\n"
            "Not interested? Reply STOP to opt out.\n"
            "Help? {{whatsapp_link}}"
        ),
    ),
    "monthly_promo_whatsapp": AutomationTemplate(
        key="monthly_promo_whatsapp",
        channel="whatsapp",
        title="Monthly Website Reorder",
        category="marketing",
        subject=None,
        meta_template_name="pureleven_monthly_reorder",
        meta_category="MARKETING",
        body=(
            "Hi {{customer_name}}, your next Pureleven refill is just a few taps away.\n\n"
            "Order fresh products from our website: {{website_url}}\n"
            "Need help choosing or repeating your last order? Message us here: {{whatsapp_link}}\n\n"
            "Reply STOP to pause automated messages."
        ),
    ),
    "monthly_promo_email": AutomationTemplate(
        key="monthly_promo_email",
        channel="email",
        title="Monthly Website Reorder Email",
        category="marketing",
        subject="Your next Pureleven order is ready when you are",
        body=(
            "Hi {{customer_name}},\n\n"
            "We would love to serve your next Pureleven order. You can browse and purchase products directly from our website:\n"
            "{{website_url}}\n\n"
            "For help choosing products or repeating a previous order, message us on WhatsApp:\n"
            "{{whatsapp_link}}\n\n"
            "Thank you for choosing Pureleven.\n"
            "Pureleven Team"
        ),
    ),
    "delivery_thanks": AutomationTemplate(
        key="delivery_thanks",
        channel="whatsapp",
        title="Thank You - Order Delivered with Feedback Request",
        category="utility",
        subject=None,
        meta_template_name="pureleven_delivery_thanks",
        meta_category="UTILITY",
        body=(
            "Hi {{customer_name}}, your Pureleven order *{{order_number}}* has been delivered! 🎉\n\n"
            "Thank you for your purchase. We'd love to hear your feedback:\n"
            "• How was the product quality?\n"
            "• How was the delivery experience?\n"
            "• Anything we can improve?\n\n"
            "Reply here or visit: {{website_url}}\n\n"
            "Any issues? Message us immediately: {{whatsapp_link}}"
        ),
    ),
    "product_promo_60day": AutomationTemplate(
        key="product_promo_60day",
        channel="whatsapp",
        title="Product Reorder - 60 Days After Purchase",
        category="marketing",
        subject=None,
        meta_template_name="pureleven_60day_reorder",
        meta_category="MARKETING",
        body=(
            "Hi {{customer_name}}, time to refresh! 🛍️\n\n"
            "It's been 60 days since your last Pureleven order.\n\n"
            "Browse fresh products & special offers:\n"
            "{{website_url}}\n\n"
            "Need recommendations? Just ask us:\n"
            "{{whatsapp_link}}\n\n"
            "Reply STOP to opt out of promotions."
        ),
    ),
    "website_reminder_90day": AutomationTemplate(
        key="website_reminder_90day",
        channel="whatsapp",
        title="Website Order Reminder - 90 Days After Purchase",
        category="marketing",
        subject=None,
        meta_template_name="pureleven_website_reminder_90day",
        meta_category="MARKETING",
        body=(
            "Hi {{customer_name}}, it's been 3 months! 📲\n\n"
            "Ready to reorder from Pureleven?\n\n"
            "Shop now: www.pureleven.com\n\n"
            "Browse our full range of products or repeat your last order with just one click.\n\n"
            "Need help? Message us here: {{whatsapp_link}}\n\n"
            "Reply STOP to opt out of updates."
        ),
    ),
}


def template_catalog() -> list[dict]:
    return [
        {
            "key": template.key,
            "channel": template.channel,
            "title": template.title,
            "category": template.category,
            "subject": template.subject,
            "body": template.body,
            "meta_template_name": template.meta_template_name,
            "meta_category": template.meta_category,
            "language": template.language,
        }
        for template in TEMPLATES.values()
    ]
