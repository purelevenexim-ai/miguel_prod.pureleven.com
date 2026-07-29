"""
Performance monitoring and baseline tracking for API endpoints.
Captures request timing, database query counts, and response metrics.
"""

import json
import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Callable
from functools import wraps
from pathlib import Path

logger = logging.getLogger(__name__)

# Baseline metrics storage (in-memory + optional disk)
BASELINE_FILE = Path("/opt/pureleven/backend/performance_baselines.json")
_baseline_cache: Dict[str, Dict[str, Any]] = {}


class PerformanceMetric:
    """Represents a single performance measurement."""
    
    def __init__(self, endpoint: str, method: str, status_code: int = 200):
        self.endpoint = endpoint
        self.method = method
        self.status_code = status_code
        self.start_time = time.time()
        self.start_datetime = datetime.now(timezone.utc)
        self.duration_ms = None
        self.db_queries = 0
        self.response_size_bytes = 0
    
    def end(self) -> None:
        """Mark the end of the metric collection."""
        self.duration_ms = (time.time() - self.start_time) * 1000
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize metric to dictionary."""
        return {
            "endpoint": self.endpoint,
            "method": self.method,
            "status_code": self.status_code,
            "duration_ms": round(self.duration_ms, 2) if self.duration_ms else None,
            "db_queries": self.db_queries,
            "response_size_bytes": self.response_size_bytes,
            "timestamp": self.start_datetime.isoformat(),
        }


class PerformanceBaseline:
    """Stores baseline metrics for endpoints and allows comparative analysis."""
    
    def __init__(self):
        self._metrics: Dict[str, list] = {}
        self.load_from_disk()
    
    def load_from_disk(self) -> None:
        """Load baselines from disk if available."""
        global _baseline_cache
        if BASELINE_FILE.exists():
            try:
                with open(BASELINE_FILE) as f:
                    _baseline_cache = json.load(f)
                logger.info(f"Loaded {len(_baseline_cache)} endpoint baselines from disk")
            except Exception as e:
                logger.error(f"Failed to load baseline file: {e}")
    
    def save_to_disk(self) -> None:
        """Save baselines to disk."""
        try:
            BASELINE_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(BASELINE_FILE, 'w') as f:
                json.dump(_baseline_cache, f, indent=2)
            logger.info(f"Saved baselines to {BASELINE_FILE}")
        except Exception as e:
            logger.error(f"Failed to save baseline file: {e}")
    
    def record_metric(self, metric: PerformanceMetric) -> None:
        """Record a single metric."""
        key = f"{metric.method} {metric.endpoint}"
        if key not in _baseline_cache:
            _baseline_cache[key] = {
                "endpoint": metric.endpoint,
                "method": metric.method,
                "measurements": [],
                "baseline_duration_ms": None,
                "baseline_db_queries": None,
            }
        
        _baseline_cache[key]["measurements"].append(metric.to_dict())
        
        # Keep only last 100 measurements per endpoint
        if len(_baseline_cache[key]["measurements"]) > 100:
            _baseline_cache[key]["measurements"] = _baseline_cache[key]["measurements"][-100:]
    
    def get_stats_for_endpoint(self, endpoint: str, method: str = "GET") -> Optional[Dict[str, Any]]:
        """Get aggregated stats for a specific endpoint."""
        key = f"{method} {endpoint}"
        if key not in _baseline_cache:
            return None
        
        measurements = _baseline_cache[key]["measurements"]
        if not measurements:
            return None
        
        durations = [m["duration_ms"] for m in measurements if m["duration_ms"]]
        db_queries = [m["db_queries"] for m in measurements if m.get("db_queries") is not None]
        
        return {
            "endpoint": endpoint,
            "method": method,
            "measurement_count": len(measurements),
            "duration_ms": {
                "min": min(durations) if durations else None,
                "max": max(durations) if durations else None,
                "avg": sum(durations) / len(durations) if durations else None,
                "latest": durations[-1] if durations else None,
            },
            "db_queries": {
                "min": min(db_queries) if db_queries else None,
                "max": max(db_queries) if db_queries else None,
                "avg": sum(db_queries) / len(db_queries) if db_queries else None,
                "latest": db_queries[-1] if db_queries else None,
            },
            "last_measured": measurements[-1]["timestamp"],
        }
    
    def create_baseline_report(self) -> Dict[str, Any]:
        """Generate a comprehensive baseline report for all monitored endpoints."""
        report = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "endpoints": {},
            "summary": {
                "total_endpoints": len(_baseline_cache),
                "slowest_endpoints": [],
                "most_queries": [],
            }
        }
        
        stats_list = []
        for key in _baseline_cache.keys():
            parts = key.split(" ", 1)
            if len(parts) == 2:
                method, endpoint = parts
                stats = self.get_stats_for_endpoint(endpoint, method)
                if stats:
                    report["endpoints"][key] = stats
                    stats_list.append((key, stats))
        
        # Find slowest and most query-heavy endpoints
        slowest = sorted(
            stats_list,
            key=lambda x: x[1]["duration_ms"]["avg"] or 0,
            reverse=True
        )[:5]
        most_queries = sorted(
            stats_list,
            key=lambda x: x[1]["db_queries"]["avg"] or 0,
            reverse=True
        )[:5]
        
        report["summary"]["slowest_endpoints"] = [
            {"endpoint": k, "avg_duration_ms": v["duration_ms"]["avg"]}
            for k, v in slowest
        ]
        report["summary"]["most_queries"] = [
            {"endpoint": k, "avg_queries": v["db_queries"]["avg"]}
            for k, v in most_queries
        ]
        
        return report


# Global singleton
_baseline = PerformanceBaseline()


def measure_performance(endpoint: str = "", method: str = "GET"):
    """
    Decorator to measure and record performance of FastAPI endpoints or functions.
    
    Example:
        @measure_performance(endpoint="/api/orders", method="GET")
        async def list_orders(...):
            ...
    """
    def decorator(fn: Callable) -> Callable:
        @wraps(fn)
        async def async_wrapper(*args, **kwargs) -> Any:
            ep = endpoint or fn.__name__
            metric = PerformanceMetric(ep, method)
            try:
                result = await fn(*args, **kwargs)
                metric.status_code = 200
            except Exception as e:
                metric.status_code = 500
                raise
            finally:
                metric.end()
                _baseline.record_metric(metric)
            return result
        
        @wraps(fn)
        def sync_wrapper(*args, **kwargs) -> Any:
            ep = endpoint or fn.__name__
            metric = PerformanceMetric(ep, method)
            try:
                result = fn(*args, **kwargs)
                metric.status_code = 200
            except Exception as e:
                metric.status_code = 500
                raise
            finally:
                metric.end()
                _baseline.record_metric(metric)
            return result
        
        # Return appropriate wrapper based on function
        if hasattr(fn, '__await__'):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


def get_performance_baseline() -> PerformanceBaseline:
    """Get the global performance baseline instance."""
    return _baseline


def save_performance_snapshot() -> Dict[str, Any]:
    """
    Create and save a performance baseline snapshot.
    Returns the baseline report.
    """
    report = _baseline.create_baseline_report()
    _baseline.save_to_disk()
    logger.info(f"Performance snapshot saved with {len(report['endpoints'])} endpoints")
    return report
