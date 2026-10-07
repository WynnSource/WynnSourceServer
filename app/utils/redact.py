from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


def redact_query(query: str) -> str:
    """Keep parameter names, drop values: manage endpoints carry user tokens in the query."""
    return urlencode([(k, "REDACTED") for k, _ in parse_qsl(query, keep_blank_values=True)], safe="")


def redact_url(value: str) -> str:
    """``redact_query`` applied to the query part of a URL or request target."""
    parts = urlsplit(value)
    return urlunsplit(parts._replace(query=redact_query(parts.query))) if parts.query else value


__all__ = ["redact_query", "redact_url"]
