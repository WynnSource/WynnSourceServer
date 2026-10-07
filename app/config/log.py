from pydantic import Field
from pydantic_settings import BaseSettings


class LoggerConfig(BaseSettings):
    """
    Logger configuration.
    """

    level: str = "DEBUG"
    format: str = (
        "<g>{time:YY-MM-DD HH:mm:ss}</g>"
        + "[<lvl>{level: <8}</lvl>]"
        + "<c><u>{name}:{line}</u></c>"
        + " | {message}"
        + "{extra[trace]}"
    )
    # One JSON object per line instead of the text format above (deployments).
    json_output: bool = Field(alias="LOG_JSON", default=False)


LOG_CONFIG = LoggerConfig()
__all__ = [
    "LOG_CONFIG",
]
