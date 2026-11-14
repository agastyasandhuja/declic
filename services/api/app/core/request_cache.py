"""A bounded HTTP-request-local memo, never shared across requests or identities."""

from contextvars import ContextVar

request_cache: ContextVar[dict | None] = ContextVar("learning_request_cache", default=None)


def cached(key, read):
    values = request_cache.get()
    if values is None:
        return read()
    if key not in values:
        result = read()
        if len(values) >= 64:
            return result
        values[key] = result
    return values[key]


def invalidate():
    values = request_cache.get()
    if values is not None:
        values.clear()
