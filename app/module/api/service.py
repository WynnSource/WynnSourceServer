import random

import httpx
import jsonschema
import orjson
from apscheduler.triggers.interval import IntervalTrigger

from app.core.log import LOGGER
from app.core.scheduler import SCHEDULER
from wynnsource import WynnSourceItem
from wynnsource.common.enums_pb2 import RARITY_CRAFTED

from .schema import MappingType

MAPPING_BASE_URL = "https://raw.githubusercontent.com/WynnSource/schema/refs/heads/main/mapping/"
JSON_FILE_EXTENSION = ".json"
SCHEMA_FILE_EXTENSION = ".schema.json"
SCHEMA_FIELD = "$schema"


class MappingStorage:
    """
    Singleton storage class for ID to name mappings.
    """

    mappings: dict[MappingType, dict]

    def __init__(self):
        self.mappings = {}

    def get_instance(self) -> "MappingStorage":
        if not hasattr(self, "_instance"):
            self._instance = MappingStorage()
        return self._instance

    async def get_mapping(self, mapping_type: MappingType) -> dict:
        if mapping_type in self.mappings:
            return self.mappings[mapping_type]
        await self.update_mapping(mapping_type)
        return self.mappings.get(mapping_type, {})

    async def update_mapping(self, mapping_type: MappingType):
        url = f"{MAPPING_BASE_URL}{mapping_type.value}{JSON_FILE_EXTENSION}"
        schema_url = f"{MAPPING_BASE_URL}{mapping_type.value}{SCHEMA_FILE_EXTENSION}"
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            if response.status_code != 200:
                LOGGER.error(
                    f"Failed to fetch mapping for {mapping_type.value} "
                    + "from {url}: {response.status_code}"
                )
                return
            schema_response = await client.get(schema_url)
            if schema_response.status_code != 200:
                LOGGER.error(
                    f"Failed to fetch schema for {mapping_type.value} "
                    + "from {schema_url}: {schema_response.status_code}"
                )
                return

            mapping = orjson.loads(response.text)
            schema = orjson.loads(schema_response.text)

            try:
                jsonschema.validate(instance=mapping, schema=schema)
            except jsonschema.ValidationError as e:
                LOGGER.error(
                    f"Mapping data for {mapping_type.value} failed schema validation: {e.message}"
                )
                return

            del mapping[
                SCHEMA_FIELD
            ]  # we don't need the schema reference as it's relative path in the repo
            self.mappings[mapping_type] = mapping


@SCHEDULER.scheduled_job(
    IntervalTrigger(minutes=60),
    id="mapping_update_trigger",
    name="Mapping Update",
    misfire_grace_time=300,
)
async def update_mapping():
    """
    Scheduled job to update ID to name mappings every hour.
    """
    storage = MappingStorage().get_instance()
    for mapping_type in MappingType:
        await storage.update_mapping(mapping_type)


def generate_random_item() -> bytes:
    """
    Generate a random item for testing purposes.
    """
    id = random.randint(1, 10000)
    return WynnSourceItem(
        name=f"Test Item {id}", level=id % 100, rarity=RARITY_CRAFTED
    ).SerializeToString()
