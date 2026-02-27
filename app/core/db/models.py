"""
This is a file for alembic to load all models for autogeneration.
It should not be imported anywhere else.
"""

import app.core.security.model
import app.module.beta.model
import app.module.pool.model  # noqa: F401

__all__ = []
