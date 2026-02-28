from collections.abc import Sequence

from sqlalchemy import LargeBinary, String, UniqueConstraint, select
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, BaseRepository
from wynnsource import WynnSourceItem


class BetaItem(Base):
    __tablename__ = "beta_items"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    item: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)

    __table_args__ = (UniqueConstraint("name", name="uq_beta_item_name"),)


class BetaItemRepository(BaseRepository):
    async def add_item(self, item: WynnSourceItem) -> BetaItem:
        existing = (
            await self.session.execute(select(BetaItem).where(BetaItem.name == item.name))
        ).scalar_one_or_none()
        if existing:
            raise ValueError("Item already exists in beta list")
        beta_item = BetaItem(name=item.name, item=item.SerializeToString())
        self.session.add(beta_item)
        await self.session.flush()
        await self.session.refresh(beta_item)
        return beta_item

    async def list_items(self) -> Sequence[BetaItem]:
        result = await self.session.execute(select(BetaItem))
        return result.scalars().all()
