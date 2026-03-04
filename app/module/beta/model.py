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
    async def add_item(self, item: WynnSourceItem):
        existing = (await self.session.execute(select(BetaItem).where(BetaItem.name == item.name))).scalar_one_or_none()
        if existing:
            existing.item = item.SerializeToString()
            self.session.add(existing)
        else:
            beta_item = BetaItem(name=item.name, item=item.SerializeToString())
            self.session.add(beta_item)
        await self.session.flush()

    async def get_item(self, name: str) -> BetaItem | None:
        result = await self.session.execute(select(BetaItem).where(BetaItem.name == name))
        return result.scalar_one_or_none()

    async def get_items_by_names(self, names: list[str]) -> Sequence[BetaItem]:
        result = await self.session.execute(select(BetaItem).where(BetaItem.name.in_(names)))
        return result.scalars().all()

    async def list_items(self) -> Sequence[BetaItem]:
        result = await self.session.execute(select(BetaItem))
        return result.scalars().all()

    async def delete_item(self, name: str) -> None:
        result = await self.session.execute(select(BetaItem).where(BetaItem.name == name))
        beta_item = result.scalar_one_or_none()
        if beta_item:
            await self.session.delete(beta_item)
            await self.session.flush()
