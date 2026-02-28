import enum


class ErrorCodes(enum.StrEnum):
    """
    Enum for error codes.
    """

    OK = "OK"
    UNKNOWN_ERROR = "UNKNOWN_ERROR"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    NOT_FOUND = "NOT_FOUND"
    HTTP_ERROR = "HTTP_ERROR"
