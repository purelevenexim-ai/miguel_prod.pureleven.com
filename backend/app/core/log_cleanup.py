"""
Log Cleanup Scheduler
──────────────────────
Runs in background thread every 30 minutes.
Deletes ActivityLog rows where expires_at < now().
Keeps the table small — max ~6 hours of data per tenant at any time.
"""

import threading
import time
import logging

logger = logging.getLogger("miguel.log_cleanup")

_INTERVAL_SECONDS = 30 * 60   # every 30 minutes
_stop_event = threading.Event()


def _cleanup_loop():
    """Background thread: purge expired logs every 30 minutes."""
    # Delay first run by 2 minutes to let the app fully start
    time.sleep(120)

    while not _stop_event.is_set():
        try:
            from app.database.session import SessionLocal
            from app.core.logger import purge_expired_logs

            db = SessionLocal()
            try:
                count = purge_expired_logs(db)
                if count > 0:
                    logger.info(f"[LogCleanup] Purged {count} expired log entries.")
            finally:
                db.close()

        except Exception as exc:
            logger.warning(f"[LogCleanup] Error during cleanup: {exc}")

        _stop_event.wait(timeout=_INTERVAL_SECONDS)


_thread: threading.Thread | None = None


def start_cleanup_scheduler():
    """Call once at app startup. Starts the background cleanup thread."""
    global _thread
    if _thread is None or not _thread.is_alive():
        _thread = threading.Thread(
            target=_cleanup_loop,
            daemon=True,
            name="log-cleanup",
        )
        _thread.start()
        logger.info("[LogCleanup] Background log cleanup scheduler started.")


def stop_cleanup_scheduler():
    """Call at app shutdown."""
    _stop_event.set()
    if _thread:
        _thread.join(timeout=5)
    logger.info("[LogCleanup] Log cleanup scheduler stopped.")
