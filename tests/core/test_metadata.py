from app.core import metadata
from app.core.rate_limiter import ip_based_key_func


def test_metadata_decorator():
    @metadata.cached(expire=120)
    @metadata.permission(permission="test.permission")
    @metadata.rate_limit(limit=10, period=60)
    async def test_endpoint():
        pass

    assert hasattr(test_endpoint, "__metadata__")
    meta = test_endpoint.__metadata__
    assert meta.permission == "test.permission"

    assert meta.cache is not None
    assert meta.cache.expire == 120

    assert meta.rate_limit is not None
    assert meta.rate_limit.limit == 10
    assert meta.rate_limit.period == 60
    assert meta.rate_limit.key_func == ip_based_key_func
