from pydantic import BaseModel


class ShinyData(BaseModel):
    item: str
    tracker: str
