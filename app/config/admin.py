from pydantic import Field
from pydantic_settings import BaseSettings


class AdminConfig(BaseSettings):
    """
    Configuration for the admin interface.
    """

    token: str | None = Field(alias="WCS_ADMIN_TOKEN", default=None)


ADMIN_CONFIG = AdminConfig()  # Debugging line to check the environment variable
