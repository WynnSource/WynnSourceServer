from dataclasses import dataclass


@dataclass
class EndpointMetadata:
    """
    Metadata for an API endpoint.
    """

    permission: str | set[str] | None = None

    def __init__(self, permission: str | set[str] | None = None):
        self.permission = permission


def with_metadata(*, permission: str | set[str] | None = None):
    """
    Decorator to add metadata to an API endpoint.
    """

    def decorator(func):
        if getattr(func, "__metadata__", None) is not None:
            raise ValueError("Function already has metadata.")
        setattr(func, "__metadata__", EndpointMetadata(permission))
        return func

    return decorator


__all__ = ["EndpointMetadata", "with_metadata"]
