import enum


class ErrorCodes(enum.IntEnum):
    """
    Enum for error codes.
    """

    OK = 0
    UNKNOWN_ERROR = -1
    VALIDATION_ERROR = -2
    NOT_FOUND = -3
