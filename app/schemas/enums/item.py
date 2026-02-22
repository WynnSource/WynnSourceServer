from base64 import b64encode
from enum import StrEnum

from google.protobuf import json_format

from wynnsource import WynnSourceItem


class ItemReturnType(StrEnum):
    B64 = "b64"
    JSON = "json"
    NAME = "name"

    def format_items(self, items: list[bytes]) -> list[str] | list[dict]:
        match self:
            case ItemReturnType.B64:
                return [b64encode(item).decode() for item in items]
            case ItemReturnType.JSON:
                formatted_items = []
                for item in items:
                    try:
                        decoded = WynnSourceItem.FromString(item)
                        formatted_items.append(json_format.MessageToDict(decoded))
                    except Exception:
                        continue  # silently skip invalid items
                return formatted_items
            case ItemReturnType.NAME:
                formatted_items = []
                for item in items:
                    try:
                        decoded = WynnSourceItem.FromString(item)
                        formatted_items.append(decoded.name)
                    except Exception:
                        continue  # silently skip invalid items
                return formatted_items
