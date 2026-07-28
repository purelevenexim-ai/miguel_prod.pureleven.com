from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
import logging

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
from app.modules.message_automation.router import router as message_automation_router
from app.modules.gst.router import router as gst_router
from app.modules.shipping_config.router import router as shipping_config_router
from app.modules.shipping.router import router as shipping_router
from app.modules.shipments.router import router as shipments_router
from app.modules.shipments.tariff_router import router as tariff_upload_router
from app.modules.tenant_settings.router import router as tenant_settings_router
from app.modules.portal.router import router as portal_router
from app.modules.india_post.router import router as india_post_router
from app.modules.performance.router import router as performance_router
from app.modules.internal.router import router as internal_router
from app.modules.profit_checker.router import router as profit_checker_router
from app.modules.customer_retarget.router import router as customer_retarget_router
from app.core.log_middleware import RequestLoggingMiddleware
from app.core.performance import PerformanceMetric, get_performance_baseline
from app.core.log_cleanup import start_cleanup_scheduler, stop_cleanup_scheduler
from app.core.error_handlers import setup_error_handlers
from app.core.tracking_worker import start_tracking_worker, stop_tracking_worker
from app.core.shopify_sync_worker import start_shopify_sync_worker, stop_shopify_sync_worker
from app.core.customer_sync_worker import start_customer_sync_worker, stop_customer_sync_worker
from app.core.message_automation_worker import start_message_automation_worker, stop_message_automation_worker

app = FastAPI(title="Miguel SaaS CRM")

# ── Error handlers (must be before middleware) ─────────────────
setup_error_handlers(app)

# ── Middleware ────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Compress JSON/API responses to reduce transfer latency on large payloads.
app.add_middleware(GZipMiddleware, minimum_size=1024)

# ── Request Logging Middleware (auto-logs every write operation) ──
app.add_middleware(RequestLoggingMiddleware)


@app.middleware("http")
async def capture_request_performance(request: Request, call_next):
    """
    Capture lightweight timing baselines for authenticated API traffic.
    This keeps /api/performance populated without decorating each endpoint.
    """
    path = request.url.path
    should_track = (
        (path.startswith("/api/") or path.startswith("/tenant/") or path.startswith("/platform/"))
        and not path.startswith("/api/performance")
    )

    if not should_track:
        return await call_next(request)

    metric = PerformanceMetric(endpoint=path, method=request.method)
    baseline = get_performance_baseline()

    try:
        response = await call_next(request)
        metric.status_code = response.status_code
        content_length = response.headers.get("content-length")
        if content_length and content_length.isdigit():
            metric.response_size_bytes = int(content_length)
        return response
    except Exception:
        metric.status_code = 500
        raise
    finally:
        metric.end()
        baseline.record_metric(metric)

# ── Routers ───────────────────────────────────────────────────
app.include_router(platform_router)   # /platform/login, /platform/tenants
app.include_router(tenant_router)     # /tenant/login, /tenant/me, /tenant/employees
app.include_router(customers_router)  # /api/customers
app.include_router(leads_router)      # /api/leads
app.include_router(orders_router)     # /api/orders
app.include_router(products_router)   # /api/products
app.include_router(reporting_router)  # /api/reports
app.include_router(labels_router)     # /api/labels
app.include_router(meta_router)       # /api/meta
app.include_router(vendors_router)    # /api/vendors
app.include_router(purchases_router)  # /api/purchases
app.include_router(inventory_router)  # /api/inventory
app.include_router(invoices_router)   # /api/invoices
app.include_router(logs_router)       # /platform/logs  — SuperAdmin only
app.include_router(whatsapp_router)   # /api/whatsapp   — WhatsApp Business (legacy)
app.include_router(wa_engine_router)  # /api/wa         — WhatsApp Engine v2
app.include_router(message_automation_router)  # /api/message-automation — automated customer messaging
app.include_router(gst_router)        # /api/gst        — GST & Accounting Reports
app.include_router(shipping_config_router)  # /api/config — Shipping Configuration
app.include_router(shipping_router)         # /api/shipping — Shipping Tariffs
app.include_router(shipments_router)        # /api/shipments + /webhooks/shopify
app.include_router(tariff_upload_router)    # /api/tariff-upload — safe 2-step XLSX workflow
app.include_router(tenant_settings_router)  # /api/tenant/settings
app.include_router(portal_router)           # /api/portal — Customer self-service portal
app.include_router(india_post_router)       # /api/india-post — Tariff, pincode, tracking
app.include_router(performance_router)      # /api/performance — Performance metrics & baselines
app.include_router(internal_router)   # /api/internal
app.include_router(profit_checker_router)   # /api/profit-checker — Profit Checker module
app.include_router(customer_retarget_router)  # /api/customer-retarget — shared calling queue


@app.on_event("startup")
def on_startup():
    """Start background schedulers on app startup."""
    logger = logging.getLogger(__name__)
    try:
        logger.info("🔥 [STARTUP] Starting background workers...")
        start_cleanup_scheduler()
        start_tracking_worker()
        start_shopify_sync_worker()
        start_customer_sync_worker()
        start_message_automation_worker()
        logger.info("🔥 [STARTUP] All workers started successfully")
    except Exception as e:
        logger.error(f"🔥 [STARTUP] Error starting workers: {e}", exc_info=True)


@app.on_event("shutdown")
def on_shutdown():
    """Stop background schedulers on app shutdown."""
    stop_cleanup_scheduler()
    stop_tracking_worker()
    stop_shopify_sync_worker()
    stop_customer_sync_worker()
    stop_message_automation_worker()


@app.get("/")
def root():
    return {"message": "Miguel SaaS CRM Running"}
