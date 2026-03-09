from base64 import b64decode

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.log import LOGGER
from wynnsource import WynnSourceItem

from .config import BETA_CONFIG
from .model import BetaItemRepository
from .schema import ItemPatchSubmission, NewItemSubmission, PatchableItemField

allowed_version = BETA_CONFIG.allowed_versions


async def handle_item_submission(submission: NewItemSubmission, session: AsyncSession) -> None:
    if not any(version in submission.mod_version for version in allowed_version):
        LOGGER.debug(f"Submission version {submission.mod_version} is not allowed, skipping submission")
        return
    itemRepo = BetaItemRepository(session)
    succeeds = 0
    for item in submission.items:
        try:
            item = WynnSourceItem.FromString(b64decode(item))
            while item.name.endswith("À"):
                item.name = item.name.removesuffix("À")
            existing = await itemRepo.get_item(item.name)
            existing = WynnSourceItem.FromString(existing.item) if existing else None
            if existing and item == existing:
                LOGGER.debug(f"Item from submission is identical to existing item: {item.name}")
                continue
            if existing and item != existing:
                LOGGER.debug(f"Item from submission is different from existing item: {item.name}," + " overwriting")
            if existing and existing.gear.powders:
                item.gear.powders.extend(existing.gear.powders)
            await itemRepo.add_item(item)
            succeeds += 1
        except Exception as e:
            LOGGER.debug(f"Failed to add item from submission, error: {e}")
            # Silently ignore failed items
            pass

    LOGGER.info(f"Processed {succeeds}/{len(submission.items)} items from beta submission")


async def get_beta_items(session: AsyncSession) -> list[bytes]:
    itemRepo = BetaItemRepository(session)
    beta_items = await itemRepo.list_items()
    deserialized_items = [WynnSourceItem.FromString(item.item) for item in beta_items]
    return [WynnSourceItem.SerializeToString(item) for item in deserialized_items if item.HasField("gear")]


async def get_beta_ingredients(session: AsyncSession) -> list[bytes]:
    itemRepo = BetaItemRepository(session)
    beta_items = await itemRepo.list_items()
    deserialized_items = [WynnSourceItem.FromString(item.item) for item in beta_items]
    return [WynnSourceItem.SerializeToString(item) for item in deserialized_items if item.HasField("ingredient")]


async def get_beta_items_by_name(session: AsyncSession, name: list[str]) -> list[bytes]:
    itemRepo = BetaItemRepository(session)
    beta_items = await itemRepo.get_items_by_names(name)
    deserialized_items = [WynnSourceItem.FromString(item.item) for item in beta_items]
    return [WynnSourceItem.SerializeToString(item) for item in deserialized_items if item.HasField("gear")]


async def get_beta_ingredients_by_name(session: AsyncSession, name: list[str]) -> list[bytes]:
    itemRepo = BetaItemRepository(session)
    beta_items = await itemRepo.get_items_by_names(name)
    deserialized_items = [WynnSourceItem.FromString(item.item) for item in beta_items]
    return [WynnSourceItem.SerializeToString(item) for item in deserialized_items if item.HasField("ingredient")]


async def handle_patch_submission(submission: ItemPatchSubmission, session: AsyncSession) -> None:
    if not any(version in submission.mod_version for version in allowed_version):
        LOGGER.debug(f"Submission version {submission.mod_version} is not allowed, skipping submission")
        return
    itemRepo = BetaItemRepository(session)
    succeeds = 0
    match submission.patch:
        case PatchableItemField.POWDER:
            for item in submission.items:
                try:
                    item = WynnSourceItem.FromString(b64decode(item))
                    existing = await itemRepo.get_item(item.name)
                    if not existing:
                        LOGGER.debug(f"Item from patch submission does not exist in beta: {item.name}")
                        continue
                    existing_item = WynnSourceItem.FromString(existing.item)
                    del existing_item.gear.powders[:]
                    existing_item.gear.powders.extend(item.gear.powders)
                    await itemRepo.add_item(existing_item)
                    succeeds += 1
                except Exception as e:
                    LOGGER.debug(f"Failed to patch item from submission, error: {e}")
                    # Silently ignore failed items
                    pass

    LOGGER.info(f"Processed {succeeds}/{len(submission.items)} items from beta patch submission")


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


async def fix_items(session: AsyncSession) -> int:
    itemRepo = BetaItemRepository(session)
    beta_items = await itemRepo.list_items()
    fixed_count = 0
    for item in beta_items:
        try:
            existing = WynnSourceItem.FromString(item.item)
            previous_name = existing.name
            if existing.name.endswith("À"):
                while existing.name.endswith("À"):
                    existing.name = existing.name.removesuffix("À")

                await itemRepo.add_item(existing)
                await itemRepo.delete_item(previous_name)
                fixed_count += 1
        except Exception:
            continue

    return fixed_count
