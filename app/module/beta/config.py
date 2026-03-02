from typing import Annotated

from pydantic import Field
from pydantic_settings import BaseSettings

from app.core.log import LOGGER


class BetaConfig(BaseSettings):
    _beta_allowed_versions: Annotated[str, Field(alias="BETA_ALLOWED_VERSIONS")] = ""

    @property
    def allowed_versions(self) -> list[str]:
        return [version.strip() for version in self._beta_allowed_versions.split(",")]


BETA_CONFIG = BetaConfig()
LOGGER.info(f"Loaded beta config with allowed versions: {BETA_CONFIG.allowed_versions}")

__all__ = ["BETA_CONFIG"]
