#!/usr/bin/env python3
"""Import an old WhatsApp contact export as tagged CRM customers.

Dry-run is the default. Pass --apply to commit. Existing customers are matched
tenant-locally by any normalized phone and receive the Old Customers tag
without overwriting their profile or order data.
"""

import argparse
from pathlib import Path
import re

from sqlalchemy import func

from app.database.session import SessionLocal
from app.models.customer import (
    Customer,
    CustomerInteraction,
    CustomerTag,
    CustomerTagMap,
    CustomerType,
    LeadStatus,
    SourceType,
)
from app.models.employee import Employee, RoleEnum
from app.models.tenant import Tenant
from app.modules.customers.service import generate_customer_code


TAG_NAME = "Old Customers"
LINE_PATTERN = re.compile(
    r"^\s*(\d+)\.\s*(.*?)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*$"
)


def phone_key(value: str) -> str:
    digits = re.sub(r"\D", "", value or "")
    if len(digits) == 12 and digits.startswith("91"):
        return digits[-10:]
    if len(digits) == 11 and digits.startswith("0"):
        return digits[-10:]
    return digits


def display_phone(value: str) -> str:
    digits = re.sub(r"\D", "", value or "")
    if not digits:
        return ""
    if len(digits) == 10:
        return f"+91{digits}"
    if len(digits) == 11 and digits.startswith("0"):
        return f"+91{digits[1:]}"
    return f"+{digits}"


def parse_contacts(path: Path) -> list[dict]:
    contacts = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        match = LINE_PATTERN.match(raw_line)
        if not match:
            continue
        source_number, name, category, phone_text = match.groups()
        if name.strip() == "--":
            continue
        phones = []
        for candidate in phone_text.split(","):
            formatted = display_phone(candidate)
            if formatted and phone_key(formatted) not in {
                phone_key(item) for item in phones
            }:
                phones.append(formatted)
        contacts.append(
            {
                "source_number": int(source_number),
                "name": name.strip(),
                "category": category.strip(),
                "phones": phones,
            }
        )
    return contacts


def customer_type_for(category: str):
    lowered = category.lower()
    if "distributor" in lowered:
        return CustomerType.distributor
    if "wholesale" in lowered or "bulk" in lowered:
        return CustomerType.wholesale
    if "retail" in lowered or "customer" in lowered:
        return CustomerType.retail
    return None


def ensure_tag(db, tenant_id):
    tag = (
        db.query(CustomerTag)
        .filter(
            CustomerTag.tenant_id == tenant_id,
            func.lower(CustomerTag.name) == TAG_NAME.lower(),
        )
        .first()
    )
    if tag is None:
        tag = CustomerTag(tenant_id=tenant_id, name=TAG_NAME)
        db.add(tag)
        db.flush()
    return tag


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", required=True, type=Path)
    parser.add_argument("--tenant-slug", required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    contacts = parse_contacts(args.file)
    db = SessionLocal()
    try:
        tenant = (
            db.query(Tenant)
            .filter(Tenant.slug == args.tenant_slug, Tenant.is_active.is_(True))
            .first()
        )
        if tenant is None:
            raise SystemExit(f"Active tenant not found: {args.tenant_slug}")
        employee = (
            db.query(Employee)
            .filter(
                Employee.tenant_id == tenant.id,
                Employee.is_active.is_(True),
                Employee.role == RoleEnum.admin,
            )
            .order_by(Employee.email.asc())
            .first()
        )
        if employee is None:
            raise SystemExit("An active tenant admin is required for attribution")

        existing_customers = (
            db.query(Customer)
            .filter(Customer.tenant_id == tenant.id)
            .all()
        )
        by_phone = {}
        for customer in existing_customers:
            for value in [customer.phone, customer.alternate_phone]:
                key = phone_key(value or "")
                if key:
                    by_phone.setdefault(key, customer)

        existing_tagged_ids = {
            row[0]
            for row in (
                db.query(CustomerTagMap.customer_id)
                .join(CustomerTag, CustomerTag.id == CustomerTagMap.tag_id)
                .filter(
                    CustomerTagMap.tenant_id == tenant.id,
                    func.lower(CustomerTag.name) == TAG_NAME.lower(),
                )
                .all()
            )
        }
        old_names_without_phone = {
            customer.name.casefold()
            for customer in existing_customers
            if customer.id in existing_tagged_ids and not phone_key(customer.phone)
        }

        new_contacts = []
        matched = []
        seen_input_keys = {}
        duplicate_input = []
        for contact in contacts:
            keys = [phone_key(value) for value in contact["phones"] if phone_key(value)]
            duplicate = next(
                (seen_input_keys[key] for key in keys if key in seen_input_keys),
                None,
            )
            if duplicate is not None:
                duplicate_input.append((contact, duplicate))
                continue
            for key in keys:
                seen_input_keys[key] = contact["source_number"]

            customer = next(
                (by_phone[key] for key in keys if key in by_phone),
                None,
            )
            if customer is None and not keys:
                if contact["name"].casefold() in old_names_without_phone:
                    continue
            if customer is None:
                new_contacts.append(contact)
            else:
                matched.append((contact, customer))

        print(f"Tenant: {tenant.slug}")
        print(f"Parsed contacts: {len(contacts)}")
        print(f"New customers: {len(new_contacts)}")
        print(f"Matched existing customers: {len(matched)}")
        print(f"Input duplicates skipped: {len(duplicate_input)}")
        print(
            "Contacts without phone: "
            f"{sum(1 for contact in contacts if not contact['phones'])}"
        )
        print(f"Mode: {'APPLY' if args.apply else 'DRY RUN'}")

        if not args.apply:
            db.rollback()
            return

        tag = ensure_tag(db, tenant.id)
        tagged_existing = 0
        for _, customer in matched:
            if customer.id not in existing_tagged_ids:
                db.add(
                    CustomerTagMap(
                        tenant_id=tenant.id,
                        customer_id=customer.id,
                        tag_id=tag.id,
                    )
                )
                existing_tagged_ids.add(customer.id)
                tagged_existing += 1

        created = 0
        for contact in new_contacts:
            phones = contact["phones"]
            extra_phones = phones[2:]
            note_lines = [
                "Imported from old WhatsApp contact list.",
                f"Legacy category: {contact['category']}",
                "Historical purchase date and products are unavailable.",
            ]
            if extra_phones:
                note_lines.append(
                    "Additional legacy phones: " + ", ".join(extra_phones)
                )
            customer = Customer(
                tenant_id=tenant.id,
                unique_customer_code=generate_customer_code(db, tenant.id),
                name=contact["name"],
                phone=phones[0] if phones else "",
                alternate_phone=phones[1] if len(phones) > 1 else None,
                country="India",
                customer_type=customer_type_for(contact["category"]),
                source=SourceType.whatsapp,
                lead_status=LeadStatus.new,
                created_by_employee_id=employee.id,
                notes="\n".join(note_lines),
                is_active=True,
            )
            db.add(customer)
            db.flush()
            db.add(
                CustomerTagMap(
                    tenant_id=tenant.id,
                    customer_id=customer.id,
                    tag_id=tag.id,
                )
            )
            db.add(
                CustomerInteraction(
                    tenant_id=tenant.id,
                    customer_id=customer.id,
                    employee_id=employee.id,
                    interaction_type="note",
                    message_content="Imported from old WhatsApp contact list",
                    old_status=None,
                    new_status=LeadStatus.new,
                )
            )
            for value in phones:
                key = phone_key(value)
                if key:
                    by_phone[key] = customer
            created += 1

        db.commit()
        print(f"Created: {created}")
        print(f"Tagged existing: {tagged_existing}")
        print(f"Total Old Customers label: {len(existing_tagged_ids) + created}")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
