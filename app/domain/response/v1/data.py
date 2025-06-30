from pydantic import BaseModel


class Data(BaseModel):
    """
    Base data model for v1 responses.
    This can be extended to include common fields for all responses.
    """

    pass
