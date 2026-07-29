import asyncio
import json
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date

from app.database.session import SessionLocal
from app.models.customer import Customer
from app.models.message_automation import MessageAutomationTask
from app.modules.message_automation import service

TENANT_ID = uuid.UUID('4374ad45-76b5-405b-8a3d-de49710fbdc3')
CUTOFF_START_UTC = service._india_day_bounds(date(2026, 4, 15))[1]
WORKERS = 10
PROGRESS_EVERY = 25


def send_task(task_id: str) -> dict:
    db = SessionLocal()
    try:
        task = db.query(MessageAutomationTask).filter(MessageAutomationTask.id == uuid.UUID(task_id)).first()
        if task is None:
            return {'id': task_id, 'status': 'missing'}
        if task.status not in {'pending', 'failed'}:
            return {'id': task_id, 'status': str(task.status)}
        if task.status == 'failed':
            task.status = 'pending'
            task.error_reason = None
            task.next_retry_at = None

        clean_name = ' '.join(str(task.recipient_name or 'Customer').split()) or 'Customer'
        task.recipient_name = clean_name
        if isinstance(task.payload, dict):
            task.payload['customer_name'] = clean_name

        task.scheduled_at = service.now_utc()
        task.attempts = (task.attempts or 0) + 1
        result = asyncio.run(service._send_task(db, task))
        if result.get('success'):
            task.status = 'sent'
            task.sent_at = service.now_utc()
            task.provider_message_id = result.get('provider_message_id')
            task.provider_response = result
            task.error_reason = None
        elif result.get('skipped'):
            task.status = 'skipped'
            task.provider_response = result
            task.error_reason = result.get('message')
        else:
            service._mark_retry_or_failed(
                task,
                result.get('message') or 'Send failed',
                permanent=result.get('permanent_failure', False),
            )
        db.commit()
        return {'id': task_id, 'status': str(task.status), 'message': result.get('message')}
    except Exception as exc:
        db.rollback()
        task = db.query(MessageAutomationTask).filter(MessageAutomationTask.id == uuid.UUID(task_id)).first()
        if task is not None:
            service._mark_retry_or_failed(task, str(exc))
            db.commit()
        return {'id': task_id, 'status': 'error', 'error': str(exc)}
    finally:
        db.close()


def main() -> None:
    db = SessionLocal()
    try:
        eligible_customers = (
            db.query(Customer)
            .filter(
                Customer.tenant_id == TENANT_ID,
                Customer.is_active.is_(True),
                Customer.phone.isnot(None),
                Customer.last_order_date.isnot(None),
                Customer.last_order_date < CUTOFF_START_UTC,
            )
            .order_by(Customer.last_order_date.asc())
            .all()
        )

        tasks = (
            db.query(MessageAutomationTask)
            .filter(
                MessageAutomationTask.tenant_id == TENANT_ID,
                MessageAutomationTask.channel == 'whatsapp',
                MessageAutomationTask.template_key == 'monthly_promo_whatsapp',
            )
            .all()
        )

        pending_by_customer = {}
        failed_by_customer = {}
        sent_customers = set()
        for task in tasks:
            if not task.customer_id:
                continue
            if task.status == 'sent':
                sent_customers.add(task.customer_id)
            elif task.status == 'pending' and task.customer_id not in pending_by_customer:
                pending_by_customer[task.customer_id] = task.id
            elif task.status == 'failed' and task.customer_id not in failed_by_customer:
                failed_by_customer[task.customer_id] = task.id

        task_ids = []
        created_new = 0
        skipped_sent = 0
        for customer in eligible_customers:
            if customer.id in sent_customers:
                skipped_sent += 1
                continue
            task_id = pending_by_customer.get(customer.id)
            if task_id is None:
                task_id = failed_by_customer.get(customer.id)
            if task_id is None:
                new_task = service.schedule_monthly_promo_whatsapp(
                    db,
                    customer=customer,
                    due_at=service.now_utc(),
                    dedupe_suffix='april_15_backfill_fast',
                )
                if new_task is None:
                    continue
                task_id = new_task.id
                created_new += 1
            task_ids.append(str(task_id))
        db.commit()

        print(json.dumps({
            'eligible_customers': len(eligible_customers),
            'task_ids': len(task_ids),
            'created_new': created_new,
            'skipped_sent': skipped_sent,
            'workers': WORKERS,
        }), flush=True)
    finally:
        db.close()

    results = []
    with ThreadPoolExecutor(max_workers=WORKERS) as executor:
        futures = [executor.submit(send_task, task_id) for task_id in task_ids]
        for index, future in enumerate(as_completed(futures), start=1):
            result = future.result()
            results.append(result)
            if index % PROGRESS_EVERY == 0:
                sent = sum(1 for row in results if row.get('status') == 'sent')
                failed = sum(1 for row in results if row.get('status') in {'failed', 'error'})
                skipped = sum(1 for row in results if row.get('status') == 'skipped')
                print(json.dumps({
                    'progress': index,
                    'sent': sent,
                    'failed': failed,
                    'skipped': skipped,
                    'remaining': len(task_ids) - index,
                }), flush=True)

    summary = {
        'eligible_customers': len(eligible_customers),
        'task_ids': len(task_ids),
        'created_new': created_new,
        'sent': sum(1 for row in results if row.get('status') == 'sent'),
        'skipped': sum(1 for row in results if row.get('status') == 'skipped'),
        'failed': sum(1 for row in results if row.get('status') in {'failed', 'error'}),
    }
    print(json.dumps(summary, default=str), flush=True)


if __name__ == '__main__':
    main()
