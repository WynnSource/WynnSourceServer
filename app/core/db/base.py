from typing import dataclass_transform

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase


@dataclass_transform()
class Base(DeclarativeBase):
    """
    Base class for all SQLAlchemy models.
    """


class BaseRepository:
    session: AsyncSession

    def __init__(self, session: AsyncSession):
        self.session = session
