from base64 import b64decode

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.log import LOGGER
from wynnsource import WynnSourceItem
from wynnsource.item.gear_pb2 import GearType

from .model import BetaItemRepository
from .schema import NewItemSubmission

allowed_version = ["0.2.2"]


async def handle_item_submission(submission: NewItemSubmission, session: AsyncSession) -> None:
    if not any(version in submission.mod_version for version in allowed_version):
        LOGGER.debug(
            f"Submission version {submission.mod_version} is not allowed, skipping submission"
        )
        return
    itemRepo = BetaItemRepository(session)
    succeeds = 0
    for item in submission.items:
        try:
            item = WynnSourceItem.FromString(b64decode(item))
            existing = await itemRepo.get_item(item.name)
            existing = WynnSourceItem.FromString(existing.item) if existing else None
            if not check_item_validity(item):
                LOGGER.debug(f"Item from submission is invalid: {item.name}")
                continue
            if existing and item == existing:
                LOGGER.debug(f"Item from submission is identical to existing item: {item.name}")
                continue
            if existing and item != existing:
                LOGGER.debug(
                    f"Item from submission is different from existing item: {item.name},"
                    + " overwriting"
                )
            await itemRepo.add_item(item)
            succeeds += 1
        except Exception as e:
            LOGGER.debug(f"Failed to add item from submission, error: {e}")
            # Silently ignore failed items
            pass

    LOGGER.info(f"Processed {succeeds}/{len(submission.items)} items from beta submission")


def check_item_validity(item: WynnSourceItem) -> bool:
    if item.name == "":
        return False
    if item.level == 0:
        return False
    if item.rarity == 0:
        return False
    if not item.HasField("gear"):
        return False
    if item.gear.type == 0:
        return False
    if not item.gear.HasField("requirements"):
        return False
    if not item.gear.HasField("unidentified"):
        return False
    if len(item.gear.unidentified.identifications) == 0:
        return False
    if (
        item.gear.type
        in [
            GearType.GEAR_TYPE_BOW,
            GearType.GEAR_TYPE_WAND,
            GearType.GEAR_TYPE_DAGGER,
            GearType.GEAR_TYPE_SPEAR,
            GearType.GEAR_TYPE_RELIK,
        ]
    ) and not item.gear.HasField("weapon_stats"):
        return False
    if not item.gear.HasField("armor_stats"):
        return False

    return True


async def get_beta_items(session: AsyncSession) -> list[bytes]:
    itemRepo = BetaItemRepository(session)
    beta_items = await itemRepo.list_items()
    return [item.item for item in beta_items]


async def handle_delete_beta_items(items: list[str], session: AsyncSession):
    itemRepo = BetaItemRepository(session)
    deleted_count = 0
    for item in items:
        try:
            await itemRepo.delete_item(item)
            deleted_count += 1
        except Exception as e:
            LOGGER.debug(f"Failed to delete item: {item}, error: {e}")
            # Silently ignore failed deletions
            pass
    LOGGER.info(f"Deleted {deleted_count}/{len(items)} items from beta")


async def handle_clear_beta_items(session: AsyncSession):
    itemRepo = BetaItemRepository(session)
    beta_items = await itemRepo.list_items()
    deleted_count = 0
    for item in beta_items:
        try:
            await itemRepo.delete_item(item.name)
            deleted_count += 1
        except Exception as e:
            LOGGER.debug(f"Failed to delete item: {item.name}, error: {e}")
            # Silently ignore failed deletions
            pass
    LOGGER.info(f"Cleared {deleted_count} items from beta")
