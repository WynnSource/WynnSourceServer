import enum
import os
import tomllib


class MediaType(enum.StrEnum):
    JSON = "application/json"
    HTML = "text/html"
    TEXT = "text/plain"
    XML = "application/xml"
    FORM_URLENCODED = "application/x-www-form-urlencoded"
    MULTIPART_FORM_DATA = "multipart/form-data"

    @classmethod
    def get_media_type(cls, media_type: str) -> str:
        return cls[media_type].value if media_type in cls.__members__ else cls.JSON.value


with open("pyproject.toml", "rb") as f:
    pyproject = tomllib.load(f)

__NAME__ = "WynnSource Server"
_base_version: str = pyproject["project"]["version"]
_version_suffix = os.environ.get("WCS_VERSION_SUFFIX", "")
__VERSION__: str = f"{_base_version}{_version_suffix}" if _version_suffix else _base_version
__DESCRIPTION__: str = pyproject["project"]["description"]
__REVISION__ = 2


INJECTED_NAMESPACE = "__wcs_injected_"

__all__ = [
    "INJECTED_NAMESPACE",
    "__DESCRIPTION__",
    "__NAME__",
    "__REVISION__",
    "__VERSION__",
    "MediaType",
]
