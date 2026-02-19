from pydantic import Field
from pydantic_settings import BaseSettings


class UserConfig(BaseSettings):
    max_ip_records: int = Field(default=10, description="Maximum number of common IPs to store for each user")


USER_CONFIG = UserConfig()

__all__ = [
    "USER_CONFIG",
]
