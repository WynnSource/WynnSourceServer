from pydantic import BaseModel


class Data(BaseModel):
    """
    Base class for all v1 data models.
    """


__all__ = [
    "Data",
]
