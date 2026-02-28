from base64 import b64encode
from enum import StrEnum
from typing import Any

from google.protobuf import json_format

from wynnsource import WynnSourceItem

INVALID_PLACEHOLDER = "INVALID_ITEM"


class ItemReturnType(StrEnum):
    B64 = "b64"
    JSON = "json"
    NAME_ONLY = "name_only"

    def format_items(self, items: list[bytes]) -> list[str] | list[dict]:
        formatted: list[Any] = [self.format_item(item) for item in items]
        return formatted

    def format_item(self, item: bytes) -> str | dict:
        match self:
            case ItemReturnType.B64:
                return b64encode(item).decode()
            case ItemReturnType.JSON:
                try:
                    decoded = WynnSourceItem.FromString(item)
                    return json_format.MessageToDict(decoded)
                except Exception:
                    return INVALID_PLACEHOLDER  # return a placeholder for invalid items
            case ItemReturnType.NAME_ONLY:
                try:
                    decoded = WynnSourceItem.FromString(item)
                    return decoded.name
                except Exception:
                    return INVALID_PLACEHOLDER  # return a placeholder for invalid items
