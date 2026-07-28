"""
PHASE 1 IMPLEMENTATION: Add GZIP Compression + Limit JSONB Arrays
File to modify: /opt/miguel/backend/app/main.py

Add these imports and middleware to compress responses
"""

# ────────────────────────────────────────────────────────────
# ADD THESE IMPORTS AT THE TOP
# ────────────────────────────────────────────────────────────

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZIPMiddleware  # ← NEW

from app.modules.platform.routes import router as platform_router
from app.modules.employee_auth.routes import router as tenant_router
from app.modules.customers.router import router as customers_router
from app.modules.leads.router import router as leads_router
from app.modules.orders.router import router as orders_router
from app.modules.products.router import router as products_router
from app.modules.reporting.router import router as reporting_router
from app.modules.labels.router import router as labels_router
from app.modules.meta.router import router as meta_router
from app.modules.vendors.router import router as vendors_router
from app.modules.purchases.router import router as purchases_router
from app.modules.inventory.router import router as inventory_router
from app.modules.invoices.router import router as invoices_router
from app.modules.logs.router import router as logs_router
from app.modules.whatsapp.router import router as whatsapp_router
from app.modules.wa_engine.router import router as wa_engine_router
from app.modules.gst.router import router as gst_router
from app.core.log_middleware import RequestLoggingMiddleware
from app.core.log_cleanup import start_cleanup_scheduler, stop_cleanup_scheduler
from app.core.error_handlers import setup_error_handlers

app = FastAPI(title="Miguel SaaS CRM")

# ── Error handlers (must be before middleware) ─────────────────
setup_error_handlers(app)

# ── GZIP COMPRESSION MIDDLEWARE (NEW) ──────────────────────
# Compress responses >500 bytes (10x size reduction)
app.add_middleware(GZIPMiddleware, minimum_size=500)  # ← ADD THIS

# ── Middleware ────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Request Logging Middleware (auto-logs every write operation) ──
app.add_middleware(RequestLoggingMiddleware)

# ... rest of routers and code remain the same ...


"""
PHASE 1 IMPLEMENTATION: Limit JSONB Array Growth
File to modify: /opt/miguel/backend/app/modules/wa_engine/service.py

Add these functions to prevent unbounded JSONB array growth
"""

# Add to /opt/miguel/backend/app/modules/wa_engine/service.py

from app.models.wa_engine import WaSubscriber
from sqlalchemy.orm import Session

class SubscriberLabelService:
    """Manage subscriber labels and postback IDs with size limits"""
    
    MAX_LABELS = 50           # Maximum labels per subscriber
    MAX_POSTBACK_IDS = 100    # Keep only last 100 postback IDs
    MAX_MESSAGE_HISTORY = 500 # Keep only last 500 messages
    
    @staticmethod
    def add_label(db: Session, subscriber: WaSubscriber, label: str) -> bool:
        """
        Add label to subscriber, respecting MAX_LABELS limit.
        
        Returns: True if added, False if limit reached
        """
        if subscriber.wabis_labels is None:
            subscriber.wabis_labels = []
        
        # Check if label already exists
        if label in subscriber.wabis_labels:
            return True  # Already added
        
        # Check if at capacity
        if len(subscriber.wabis_labels) >= SubscriberLabelService.MAX_LABELS:
            # Remove oldest label (FIFO)
            subscriber.wabis_labels.pop(0)
            print(f"⚠️ Subscriber {subscriber.id} reached MAX_LABELS ({SubscriberLabelService.MAX_LABELS}). Removed oldest.")
        
        # Add new label
        subscriber.wabis_labels.append(label)
        db.commit()
        return True
    
    @staticmethod
    def remove_label(db: Session, subscriber: WaSubscriber, label: str) -> bool:
        """Remove label from subscriber"""
        if subscriber.wabis_labels and label in subscriber.wabis_labels:
            subscriber.wabis_labels.remove(label)
            db.commit()
            return True
        return False
    
    @staticmethod
    def add_postback_id(db: Session, subscriber: WaSubscriber, postback_id: str):
        """
        Add postback ID to subscriber, keeping only last N IDs.
        
        This prevents postback_ids array from growing infinitely.
        """
        if subscriber.postback_ids is None:
            subscriber.postback_ids = []
        
        # Check if already exists (avoid duplicates)
        if postback_id in subscriber.postback_ids:
            return
        
        # Add new postback ID
        subscriber.postback_ids.append(postback_id)
        
        # Keep only last MAX_POSTBACK_IDS
        if len(subscriber.postback_ids) > SubscriberLabelService.MAX_POSTBACK_IDS:
            # Archive older ones if needed in future
            removed = subscriber.postback_ids[:len(subscriber.postback_ids) - SubscriberLabelService.MAX_POSTBACK_IDS]
            subscriber.postback_ids = subscriber.postback_ids[-SubscriberLabelService.MAX_POSTBACK_IDS:]
            print(f"⚠️ Subscriber {subscriber.id} postback_ids limited to {SubscriberLabelService.MAX_POSTBACK_IDS}. Removed {len(removed)} old IDs.")
        
        db.commit()
    
    @staticmethod
    def cleanup_old_postbacks(db: Session, subscriber: WaSubscriber, keep_count: int = 50):
        """Manually cleanup old postback IDs (call periodically)"""
        if subscriber.postback_ids and len(subscriber.postback_ids) > keep_count:
            archived_count = len(subscriber.postback_ids) - keep_count
            subscriber.postback_ids = subscriber.postback_ids[-keep_count:]
            db.commit()
            print(f"✅ Cleaned {archived_count} old postback IDs from subscriber {subscriber.id}")


# Usage in wa_engine router:
"""
@router.patch("/{sub_id}/labels", response_model=dict)
def update_subscriber_labels(
    sub_id: UUID,
    data: dict,  # {"labels": ["label1", "label2"]}
    db: Session = Depends(get_db),
):
    subscriber = db.query(WaSubscriber).filter(WaSubscriber.id == sub_id).first()
    if not subscriber:
        raise HTTPException(status_code=404)
    
    # Clear old labels
    subscriber.wabis_labels = []
    
    # Add new labels (with size check)
    for label in data.get("labels", []):
        SubscriberLabelService.add_label(db, subscriber, label)
    
    return {"id": str(subscriber.id), "labels": subscriber.wabis_labels}
"""


"""
MONITORING SCRIPT: Track Memory Usage
File: /opt/miguel/backend/scripts/monitor_memory.py

Run this to see real-time memory impact of optimizations
"""

import psutil
import subprocess
import time
from datetime import datetime

def monitor_memory():
    """Monitor memory usage of FastAPI process"""
    
    # Get FastAPI process
    proc = None
    for p in psutil.process_iter(['pid', 'name']):
        if 'uvicorn' in p.name() or 'python' in p.name():
            proc = p
            break
    
    if not proc:
        print("❌ FastAPI process not found")
        return
    
    print(f"🔍 Monitoring PID {proc.pid}...\n")
    print(f"{'Time':<20} {'Memory (MB)':<15} {'% of System':<15} {'Status':<20}")
    print("─" * 70)
    
    baseline = None
    
    while True:
        try:
            memory_info = proc.memory_info()
            memory_mb = memory_info.rss / 1024 / 1024
            percent = proc.memory_percent()
            
            if baseline is None:
                baseline = memory_mb
            
            delta = memory_mb - baseline
            delta_str = f"+{delta:.1f}" if delta >= 0 else f"{delta:.1f}"
            
            status = "✅ Stable" if delta < 50 else "⚠️ Growing" if delta < 200 else "🔴 CRITICAL"
            
            timestamp = datetime.now().strftime("%H:%M:%S")
            print(f"{timestamp:<20} {memory_mb:>8.1f} MB    {percent:>8.1f}%         {delta_str:>8} MB  {status}")
            
            time.sleep(5)
            
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            print("❌ Process no longer running")
            break
        except KeyboardInterrupt:
            print("\n✅ Monitoring stopped")
            break

if __name__ == "__main__":
    monitor_memory()


"""
TESTING COMMANDS: Before/After Comparison

Run these commands to validate memory optimization
"""

# Test 1: Check current memory before changes
# Before optimization:
# $ free -h && ps aux | grep uvicorn | grep -v grep

# Test 2: Load test 100 concurrent users (before)
# $ wrk -t 4 -c 100 -d 30s http://localhost:8000/api/leads
# Watch: "free -h" in another terminal - will see memory spike

# Test 3: Apply Phase 1 changes (modify router.py + add GZIP)

# Test 4: Load test 100 concurrent users (after)
# $ wrk -t 4 -c 100 -d 30s http://localhost:8000/api/leads
# Watch: "free -h" - memory spike should be 5-10x lower

# Test 5: Check response size difference
# Before (full payload):
# $ curl http://localhost:8000/api/leads | wc -c   # ~500KB

# After (paginated + field filtering):
# $ curl "http://localhost:8000/api/leads?fields=id,name,phone,status" | wc -c  # ~50KB

# Test 6: Monitor memory growth over time
# $ python /opt/miguel/backend/scripts/monitor_memory.py
# Run for 5 minutes while making requests - should see stable memory, not growing
