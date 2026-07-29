# Perfect WhatsApp Message Journey - Implementation Guide

## Overview

This guide explains the proper implementation of the WhatsApp message automation journey to ensure:
- ✅ Only 1 message per checkpoint (no duplicates)
- ✅ Proper message sequencing by delivery status
- ✅ Automatic cancellation on order cancellation/deletion
- ✅ Correct cost calculation (24-hour window vs paid rates)

---

## Journey Checkpoints (6 Total)

### 1. Order Created (Immediate)
- **Trigger:** Order created
- **When:** Immediately (within 24-hour conversation window)
- **Template:** `order_created` (Utility)
- **Cost:** ₹0.60 (80% of ₹0.75, within 24h)
- **Dedupe Key:** `order:{order_id}:checkpoint:order_created`
- **Cancel On:** order.cancelled, order.returned
- **Max Per Customer:** 1 per order

### 2. Tracking Added (Immediate)
- **Trigger:** Tracking number added to order
- **When:** Immediately (within 24-hour conversation window)
- **Template:** `tracking_added` (Utility)
- **Cost:** ₹0.60 (80% of ₹0.75, within 24h)
- **Dedupe Key:** `order:{order_id}:checkpoint:tracking_added`
- **Cancel On:** order.cancelled, order.returned
- **Max Per Customer:** 1 per order

### 3. Tracking Update (3 Days After Tracking)
- **Trigger:** 3 days after tracking_added event
- **When:** Day 3 (may be outside 24h window)
- **Template:** `tracking_update_3day` (Utility) — renamed from `tracking_followup_3_day`
- **Cost:** ₹0.75 (full rate, likely outside 24h)
- **Dedupe Key:** `order:{order_id}:checkpoint:tracking_update_3day`
- **Cancel On:** order.cancelled, order.returned, order.delivered (don't send if already delivered)
- **Max Per Customer:** **1 ONLY** (NOT RECURRING!)
- **Critical:** This message should NOT reschedule itself

### 4. Delivery Thanks (Immediate After Delivery)
- **Trigger:** Order status changes to "delivered"
- **When:** Immediately after delivery status confirmed
- **Template:** `delivery_thanks` (Utility)
- **Cost:** ₹0.75 (full rate)
- **Dedupe Key:** `order:{order_id}:checkpoint:delivery_thanks`
- **Cancel On:** order.cancelled, order.returned (shouldn't happen after delivery)
- **Max Per Customer:** 1 per order

### 5. Review Request (15 Days After Delivery)
- **Trigger:** 15 days after order.delivered_at
- **When:** Day 15 post-delivery
- **Template:** `review_request` (Marketing)
- **Cost:** ₹1.00
- **Dedupe Key:** `order:{order_id}:checkpoint:review_request_15day`
- **Cancel On:** customer.is_active = False, customer opted out
- **Max Per Customer:** **1 ONLY per order** (NOT recurring)
- **Note:** Only send if order was actually delivered

### 6. Product Promo (60 Days After Last Purchase)
- **Trigger:** 60 days since order.delivered_at
- **When:** Day 60 post-delivery
- **Template:** `product_promo_60day` (Marketing)
- **Cost:** ₹1.00
- **Dedupe Key:** `customer:{customer_id}:checkpoint:product_promo_60day:{year-month}`
- **Cancel On:** customer.is_active = False, customer opted out
- **Max Per Customer:** **1 per month** (once per 60-day period)
- **Scope:** Customer-level (not order-level)

---

## Deduplication Strategy

### Prevent Duplicate Messages

```python
# Pseudocode for deduplication check
def should_schedule_message(checkpoint, order_id, customer_id):
    existing = MessageAutomationTask.query.filter(
        MessageAutomationTask.dedupe_key == get_dedupe_key(checkpoint, order_id, customer_id),
        MessageAutomationTask.status.in_(["pending", "sent"])
    ).first()
    
    if existing:
        return False  # Message already scheduled or sent
    return True
```

### Dedupe Keys By Checkpoint

| Checkpoint | Scope | Dedupe Key Pattern | Notes |
|-----------|-------|-------------------|-------|
| order_created | Order | `order:{id}:cp:order_created` | One per order |
| tracking_added | Order | `order:{id}:cp:tracking_added` | One per order |
| tracking_update_3day | Order | `order:{id}:cp:tracking_update_3day` | One per order (NOT repeating) |
| delivery_thanks | Order | `order:{id}:cp:delivery_thanks` | One per order |
| review_request_15day | Order | `order:{id}:cp:review_request_15day` | One per order (NOT repeating) |
| product_promo_60day | Customer+Month | `customer:{id}:cp:promo:{YYYY-MM}` | Once per customer per month |

---

## Cancellation Rules

### When Order is Cancelled
Cancel all pending messages:
```python
cancelled_messages = []
statuses_to_cancel = ["pending"]

for checkpoint in [ORDER_CREATED, TRACKING_ADDED, TRACKING_UPDATE, DELIVERY_THANKS, REVIEW_REQUEST]:
    dedupe_key = get_dedupe_key(checkpoint, order_id)
    task = MessageAutomationTask.query.filter(
        MessageAutomationTask.dedupe_key == dedupe_key,
        MessageAutomationTask.status.in_(statuses_to_cancel)
    ).first()
    
    if task:
        task.status = "cancelled"
        task.cancelled_at = now()
        task.error_reason = "Order cancelled"
        cancelled_messages.append(task)
```

### When Order is Deleted
Same as above - cancel all pending messages for this order.

### When Customer Opts Out
Cancel all pending messages for this customer:
```python
# For all customer-level checkpoints
for checkpoint in [PRODUCT_PROMO]:
    tasks = MessageAutomationTask.query.filter(
        MessageAutomationTask.customer_id == customer_id,
        MessageAutomationTask.checkpoint == checkpoint,
        MessageAutomationTask.status == "pending"
    ).all()
    
    for task in tasks:
        task.status = "cancelled"
        task.cancelled_at = now()
        task.error_reason = "Customer opted out"
```

---

## Scheduling Functions

### Core Pattern for All Checkpoints

```python
def schedule_checkpoint(
    db: Session,
    order_id: uuid.UUID,
    checkpoint: JourneyCheckpoint,
    scheduled_at: datetime = None,
) -> MessageAutomationTask | None:
    
    # 1. Load order with validations
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order or order.status in TERMINAL_STATUSES:
        return None
    
    # 2. Check deduplication
    dedupe_key = get_dedupe_key(checkpoint, order_id=order_id)
    existing = db.query(MessageAutomationTask).filter(
        MessageAutomationTask.dedupe_key == dedupe_key,
        MessageAutomationTask.status.in_(["pending", "sent"])
    ).first()
    
    if existing:
        log.info(f"Message already scheduled for {checkpoint}: {dedupe_key}")
        return None  # Don't schedule duplicate
    
    # 3. Get journey rule
    rule = JOURNEY_RULES[checkpoint]
    
    # 4. Check if we should skip (e.g., order already delivered when tracking_update triggers)
    if checkpoint == JourneyCheckpoint.TRACKING_UPDATE and order.status in ["delivered"]:
        return None  # Order already delivered, skip tracking update
    
    # 5. Calculate scheduled time
    if not scheduled_at:
        if rule.trigger_days == 0:
            scheduled_at = now_utc()
        else:
            reference_time = get_trigger_time(order, rule.trigger_event)
            scheduled_at = reference_time + timedelta(days=rule.trigger_days)
    
    # 6. Render template with variables
    variables = get_order_variables(db, order)
    subject, body = render_template(rule.template_key, variables)
    
    # 7. Create task
    task = MessageAutomationTask(
        tenant_id=order.tenant_id,
        channel="whatsapp",
        template_key=rule.template_key,
        event_type=checkpoint.value,
        dedupe_key=dedupe_key,
        scheduled_at=scheduled_at,
        subject=subject,
        body=body,
        customer_id=order.customer_id,
        order_id=order.id,
        recipient_phone_e164=get_phone(order),
        recipient_name=get_customer_name(order),
        payload=variables,
        status="pending",
    )
    
    db.add(task)
    db.flush()
    
    log.info(f"Scheduled {checkpoint} for order {order.id}: {dedupe_key}")
    return task
```

---

## Trigger Points

### When to Call Each Schedule Function

| Event | Call Function | Checkpoint |
|-------|---------------|-----------|
| `order.create()` | `schedule_checkpoint()` | ORDER_CREATED |
| `order.tracking_number = xxx` | `schedule_checkpoint()` | TRACKING_ADDED + TRACKING_UPDATE |
| `order.status = "delivered"` | `schedule_checkpoint()` | DELIVERY_THANKS + REVIEW_REQUEST + PRODUCT_PROMO |
| `order.status = "cancelled"` | `cancel_order_messages()` | All |
| `order.delete()` | `cancel_order_messages()` | All |
| `customer.is_active = False` | `cancel_customer_messages()` | PRODUCT_PROMO + others |

---

## Implementation Checklist

- [ ] Create `journey.py` with `JourneyCheckpoint`, `MessageScheduleRule`, dedup logic
- [ ] Add new templates: `delivery_thanks`, `product_promo_60day`, `tracking_update_3day`
- [ ] Rewrite `schedule_*` functions to use dedup keys and single-message logic
- [ ] **REMOVE** automatic rescheduling from `schedule_tracking_added()` (line 887)
- [ ] Add `schedule_delivery_thanks()` function (triggers on order delivery)
- [ ] Add `schedule_product_promo()` function (triggers 60 days after delivery)
- [ ] Modify order status update handlers to trigger checkpoint scheduling
- [ ] Add order cancellation handler to call `cancel_order_messages()`
- [ ] Add order deletion handler to call `cancel_order_messages()`
- [ ] Add customer opt-out handler to call `cancel_customer_messages()`
- [ ] Update message worker to check cancel_on_order_status
- [ ] Add 24-hour window detection for cost calculation
- [ ] Write unit tests for deduplication logic
- [ ] Write integration tests for full journey
- [ ] Run migration to rename `tracking_followup_3_day` to `tracking_update_3day`
- [ ] Verify no pending messages exist before deploying to production

---

## Cost Tracking Example

```python
# Example: Calculate total journey cost per customer
order = db.query(Order).filter(Order.id == order_id).first()

journey_cost = 0
for checkpoint in [ORDER_CREATED, TRACKING_ADDED, TRACKING_UPDATE, 
                   DELIVERY_THANKS, REVIEW_REQUEST, PRODUCT_PROMO]:
    rule = JOURNEY_RULES[checkpoint]
    within_24h = is_within_24h_window(order.created_at, checkpoint.get_scheduled_at(order))
    cost = get_template_cost(checkpoint, rule.template_type, within_24h)
    journey_cost += cost
    print(f"{checkpoint}: ₹{cost}")

print(f"Total journey cost per customer: ₹{journey_cost}")
# Expected: ~₹4.70 per complete journey
```

---

## Testing Strategy

### Unit Tests
- Dedup key generation (all checkpoints)
- Dedup logic (prevent duplicates)
- Cancellation logic (order cancelled, order deleted, customer opted out)
- 24-hour window detection
- Cost calculation

### Integration Tests
- Full journey: order_created → tracking → delivery → review → promo
- Skip scenarios: cancelled order, returned order
- Dedup scenarios: double-trigger of same event
- Timing: verify scheduled times are correct (3 days, 15 days, 60 days)

### Manual Testing
- Create order, verify "order_created" sent
- Add tracking, verify "tracking_added" + "tracking_update_3day" scheduled for day 3
- Simulate day 3, verify "tracking_update_3day" sent (ONLY ONCE)
- Mark delivered, verify "delivery_thanks" sent
- Simulate day 15, verify "review_request" sent (ONLY ONCE)
- Simulate day 60, verify "product_promo_60day" sent
- Cancel order, verify all pending messages cancelled
- Create second order for same customer, verify proper deduplication

---

## Migration Plan

### Phase 1: Database Preparation
1. Rename `tracking_followup_3_day` template key to `tracking_update_3day` in code
2. Update `MESSAGE_AUTOMATION_TASKS` table (dedupe_key format may change)
3. Create index on `(tenant_id, dedupe_key, status)` for faster lookups

### Phase 2: Code Changes
1. Implement journey.py
2. Rewrite schedule functions
3. Add cancellation handlers
4. Deploy with feature flag (if needed)

### Phase 3: Cleanup
1. Cancel all pending `tracking_followup_3_day` messages (save costs)
2. Verify no new duplicates are being created
3. Monitor costs for 1 week
4. Disable feature flag after verification

---

## Expected Outcomes

After implementation:

| Metric | Before | After | Savings |
|--------|--------|-------|---------|
| Messages/customer/quarter | 8-10 | 5-6 | 40% |
| Cost/customer/quarter | ₹6-10 | ₹4.50 | 45% |
| Duplicate messages | 239+ | 0 | 100% |
| Tracking 3-day recurring | Yes (infinite) | No (single) | ₹22.50/month |
| Monthly waste | ₹156+ | ₹0 | 100% |

---

## Support & Troubleshooting

### Debug a Customer's Journey
```python
# Find all messages for a customer
tasks = db.query(MessageAutomationTask).filter(
    MessageAutomationTask.customer_id == customer_id
).order_by(MessageAutomationTask.created_at.desc()).all()

for task in tasks:
    print(f"{task.event_type}: {task.status} @ {task.scheduled_at}")
```

### Fix Duplicate Messages (Cleanup)
```python
# Identify duplicates
from sqlalchemy import func
duplicates = db.query(
    MessageAutomationTask.dedupe_key,
    func.count().label('count')
).filter(
    MessageAutomationTask.status.in_(["pending", "sent"])
).group_by(MessageAutomationTask.dedupe_key).having(
    func.count() > 1
).all()

# Cancel extras
for dedupe_key, count in duplicates:
    tasks = db.query(MessageAutomationTask).filter(
        MessageAutomationTask.dedupe_key == dedupe_key,
        MessageAutomationTask.status == "pending"
    ).order_by(MessageAutomationTask.created_at.desc()).all()[1:]  # Keep first, cancel rest
    
    for task in tasks:
        task.status = "cancelled"
        task.error_reason = "Duplicate cleanup"
```

---

**Version:** 1.0  
**Date:** June 20, 2026  
**Status:** Ready for Implementation
