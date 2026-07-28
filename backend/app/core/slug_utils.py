import re
from sqlalchemy.orm import Session
from app.models.tenant import Tenant


PUBLIC_EMAIL_DOMAINS = {
    "gmail.com",
    "yahoo.com",
    "outlook.com",
    "hotmail.com",
    "icloud.com",
}


def sanitize_slug(value: str) -> str:
    value = value.lower()
    value = value.replace(" ", "-")
    value = re.sub(r"[^a-z0-9-]", "", value)
    return value


def generate_base_slug_from_email(email: str) -> str:
    username, domain = email.split("@")

    if domain.lower() in PUBLIC_EMAIL_DOMAINS:
        base = username
    else:
        base = domain.split(".")[0]

    return sanitize_slug(base)


def ensure_unique_slug(db: Session, base_slug: str) -> str:
    slug = base_slug
    counter = 1

    while db.query(Tenant).filter(Tenant.slug == slug).first():
        slug = f"{base_slug}{counter}"
        counter += 1

    return slug


def generate_slug(db: Session, owner_email: str, provided_slug: str | None = None) -> str:
    """
    If provided_slug exists -> sanitize + validate uniqueness
    Else -> auto-generate from email
    """

    if provided_slug:
        base_slug = sanitize_slug(provided_slug)
    else:
        base_slug = generate_base_slug_from_email(owner_email)

    return ensure_unique_slug(db, base_slug)
