from app.core.metadata import cached, permission


def test_metadata_decorator():
    @cached(expire=120)
    @permission(permission="test.permission")
    async def test_endpoint():
        pass

    assert hasattr(test_endpoint, "__metadata__")
    meta = test_endpoint.__metadata__
    assert meta.permission == "test.permission"
    assert meta.cache is not None
    assert meta.cache.expire == 120
