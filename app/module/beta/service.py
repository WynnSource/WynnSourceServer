from base64 import b64decode

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.log import LOGGER
from wynnsource import WynnSourceItem

from .model import BetaItemRepository
from .schema import NewItemSubmission


async def handle_item_submission(submission: NewItemSubmission, session: AsyncSession) -> None:
    itemRepo = BetaItemRepository(session)
    succeeds = 0
    for item in submission.items:
        try:
            await itemRepo.add_item(WynnSourceItem.FromString(b64decode(item)))
            succeeds += 1
        except Exception as e:
            LOGGER.debug(f"Failed to add item from submission: {item}, error: {e}")
            # Silently ignore duplicate item submissions or invalid items
            pass

    LOGGER.info(f"Processed {succeeds}/{len(submission.items)} items from beta submission")


async def get_beta_items(session: AsyncSession) -> list[bytes]:
    itemRepo = BetaItemRepository(session)
    beta_items = await itemRepo.list_items()
    return [item.item for item in beta_items]
