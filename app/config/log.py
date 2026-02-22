from pydantic_settings import BaseSettings


class LoggerConfig(BaseSettings):
    """
    Logger configuration.
    """

    level: str = "DEBUG"
    format: str = "<g>{time:YY-MM-DD HH:mm:ss}</g> [<lvl>{level: <8}</lvl>] <c><u>{name}:{line}</u></c> | {message}"


LOG_CONFIG = LoggerConfig()
__all__ = [
    "LOG_CONFIG",
]
