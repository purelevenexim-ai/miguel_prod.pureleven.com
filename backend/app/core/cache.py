"""
Simple in-memory TTL cache for high-frequency query results.
Provides decorator-based caching with invalidation hooks.
"""

import hashlib
import json
import logging
from datetime import datetime, timedelta, timezone
from functools import wraps
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)


class CacheEntry:
    """Holds cached value with metadata (TTL, creation time)."""
    
    def __init__(self, value: Any, ttl_seconds: int):
        self.value = value
        self.created_at = datetime.now(timezone.utc)
        self.ttl_seconds = ttl_seconds
    
    def is_expired(self) -> bool:
        """Check if entry has exceeded its TTL."""
        age = (datetime.now(timezone.utc) - self.created_at).total_seconds()
        return age > self.ttl_seconds


class TTLCache:
    """
    Thread-safe in-memory cache with time-to-live expiration.
    Suitable for single-instance deployments.
    """
    
    def __init__(self):
        self._cache: Dict[str, CacheEntry] = {}
        self._invalidation_hooks: Dict[str, list] = {}
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache if it exists and hasn't expired."""
        if key not in self._cache:
            return None
        
        entry = self._cache[key]
        if entry.is_expired():
            del self._cache[key]
            return None
        
        return entry.value
    
    def set(self, key: str, value: Any, ttl_seconds: int = 300) -> None:
        """Set value in cache with TTL."""
        self._cache[key] = CacheEntry(value, ttl_seconds)
    
    def delete(self, key: str) -> None:
        """Delete a specific cache key."""
        self._cache.pop(key, None)
    
    def invalidate_pattern(self, pattern: str) -> None:
        """Invalidate all keys matching a pattern (e.g., 'orders:*')."""
        keys_to_delete = [k for k in self._cache.keys() if k.startswith(pattern)]
        for key in keys_to_delete:
            del self._cache[key]
        logger.info(f"Cache invalidated {len(keys_to_delete)} entries matching pattern '{pattern}'")
    
    def clear(self) -> None:
        """Clear all cached entries."""
        self._cache.clear()
    
    def register_invalidation_hook(self, cache_pattern: str, hook_fn: Callable) -> None:
        """
        Register a function to be called when cache_pattern is invalidated.
        Useful for side effects (e.g., logging, stats updates).
        """
        if cache_pattern not in self._invalidation_hooks:
            self._invalidation_hooks[cache_pattern] = []
        self._invalidation_hooks[cache_pattern].append(hook_fn)
    
    def stats(self) -> Dict[str, Any]:
        """Return cache statistics."""
        return {
            "entries": len(self._cache),
            "capacity": len(self._cache),
        }


# Global singleton cache instance
_cache = TTLCache()


def cache_ttl(ttl_seconds: int = 300, key_prefix: str = ""):
    """
    Decorator for function-level caching with TTL.
    
    Args:
        ttl_seconds: Time-to-live in seconds
        key_prefix: Optional prefix for cache key (e.g., "orders:" for orders endpoints)
    
    Example:
        @cache_ttl(ttl_seconds=600, key_prefix="orders:stats:")
        def get_order_stats(db, tenant_id, filters):
            ...
    
    Cache key is automatically generated from function name + arguments hash.
    """
    def decorator(fn: Callable) -> Callable:
        @wraps(fn)
        def wrapper(*args, **kwargs) -> Any:
            # Build cache key from function name and arguments
            # Skip 'db' and 'self' arguments for cache key
            cache_args = []
            for i, arg in enumerate(args):
                param_name = fn.__code__.co_varnames[i] if i < len(fn.__code__.co_varnames) else f"arg{i}"
                if param_name not in ('self', 'db', 'session'):
                    try:
                        # For simple types, use repr; for objects, use id
                        if isinstance(arg, (str, int, float, bool, type(None))):
                            cache_args.append(str(arg))
                        else:
                            cache_args.append(str(type(arg).__name__))
                    except:
                        cache_args.append("unknown")
            
            # Include keyword arguments in cache key
            kwargs_str = "|".join(f"{k}={v}" for k, v in sorted(kwargs.items()) if k not in ('db', 'session'))
            
            # Hash the combined signature
            sig = f"{fn.__name__}:{','.join(cache_args)}:{kwargs_str}"
            key_hash = hashlib.md5(sig.encode()).hexdigest()[:8]
            cache_key = f"{key_prefix}{fn.__name__}:{key_hash}"
            
            # Try to get from cache
            cached_value = _cache.get(cache_key)
            if cached_value is not None:
                logger.debug(f"Cache hit for {cache_key}")
                return cached_value
            
            # Cache miss — call function
            logger.debug(f"Cache miss for {cache_key} — calling {fn.__name__}")
            result = fn(*args, **kwargs)
            
            # Store in cache
            _cache.set(cache_key, result, ttl_seconds)
            return result
        
        return wrapper
    return decorator


def invalidate_cache(pattern: str) -> None:
    """
    Invalidate all cache entries matching a pattern.
    
    Example:
        invalidate_cache("orders:*")  # Clears all orders-related caches
    """
    _cache.invalidate_pattern(pattern)
    logger.info(f"Cache invalidation triggered for pattern: {pattern}")


def get_cache_instance() -> TTLCache:
    """Get the global cache instance."""
    return _cache


def cache_stats() -> Dict[str, Any]:
    """Get cache statistics."""
    return _cache.stats()
