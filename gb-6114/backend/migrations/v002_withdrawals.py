"""Append-only withdrawal ledger.

The table is registered on the shared metadata; calling create_all is
idempotent and safe for fresh and existing databases.
"""

from src.models import withdrawals  # noqa: F401
from src.models.base import metadata


def upgrade(connection):
    metadata.create_all(connection)
