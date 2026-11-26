from src.models import (  # noqa: F401  # Register the tables.
    audit,
    cases,
    reviews,
    runs,
    users,
    withdrawals,
)
from src.models.base import metadata


def upgrade(connection):
    # Version 1 is additive and fully declarative. New Core tables are picked
    # up through metadata while existing databases receive additive columns in
    # setup_schema() when necessary.
    metadata.create_all(connection)
