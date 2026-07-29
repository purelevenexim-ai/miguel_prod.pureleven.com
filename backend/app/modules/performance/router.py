"""
Performance metrics and baseline reporting endpoints.
Exposes current performance statistics and baseline data.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.core.auth.tenant import get_current_tenant_user
from app.core.performance import get_performance_baseline, save_performance_snapshot
from app.models.employee import Employee

router = APIRouter(prefix="/api/performance", tags=["performance"])


@router.get("/baseline")
def get_baseline_report(
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_tenant_user)
):
    """
    Get current performance baseline report for all monitored endpoints.
    Shows min/max/avg response times and database query counts.
    """
    baseline = get_performance_baseline()
    return baseline.create_baseline_report()


@router.post("/snapshot")
def create_performance_snapshot(
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_tenant_user)
):
    """
    Create and save a performance baseline snapshot to disk.
    This captures the current state of all endpoint metrics.
    """
    report = save_performance_snapshot()
    return {
        "status": "success",
        "message": "Performance baseline snapshot created and saved",
        "report": report,
    }


@router.get("/stats/{endpoint}")
def get_endpoint_stats(
    endpoint: str,
    method: str = "GET",
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_tenant_user)
):
    """
    Get detailed performance statistics for a specific endpoint.
    Shows min/max/avg metrics across all recorded measurements.
    """
    baseline = get_performance_baseline()
    stats = baseline.get_stats_for_endpoint(endpoint, method)
    if not stats:
        return {
            "status": "not_found",
            "message": f"No performance data for {method} {endpoint}",
        }
    return stats
