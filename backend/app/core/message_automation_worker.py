from __future__ import annotations

import asyncio
import logging
from sqlalchemy.orm import sessionmaker

from app.database.session import engine
from app.modules.message_automation.service import process_due_tasks

logger = logging.getLogger(__name__)

_worker_running = False
_worker_task = None
MESSAGE_AUTOMATION_INTERVAL_SECONDS = 60


async def run_message_automation_worker():
    global _worker_running
    logger.info("Message automation worker started")
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    while _worker_running:
        db = SessionLocal()
        try:
            result = await process_due_tasks(db, limit=50)
            if result.get("checked"):
                logger.info(
                    "Message automation processed: checked=%s sent=%s failed=%s skipped=%s cancelled=%s",
                    result.get("checked"),
                    result.get("sent"),
                    result.get("failed"),
                    result.get("skipped"),
                    result.get("cancelled"),
                )
        except Exception as exc:
            logger.error("Message automation cycle error: %s", exc, exc_info=True)
        finally:
            db.close()

        await asyncio.sleep(MESSAGE_AUTOMATION_INTERVAL_SECONDS)

    logger.info("Message automation worker stopped")


def start_message_automation_worker():
    global _worker_running, _worker_task
    if _worker_running:
        logger.warning("Message automation worker already running")
        return

    _worker_running = True
    loop = asyncio.get_event_loop()
    if loop.is_running():
        _worker_task = loop.create_task(run_message_automation_worker())
    else:
        loop.run_until_complete(run_message_automation_worker())


def stop_message_automation_worker():
    global _worker_running, _worker_task
    _worker_running = False
    if _worker_task and not _worker_task.done():
        _worker_task.cancel()
    logger.info("Message automation worker stopped")
