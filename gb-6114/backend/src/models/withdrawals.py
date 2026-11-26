from sqlalchemy import BigInteger, Column, ForeignKey, Integer, String, UniqueConstraint, Table

from .base import metadata


withdrawals = Table(
    "withdrawals",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("case_id", ForeignKey("cases.id"), nullable=False, index=True),
    Column("mass", String(24), nullable=False),
    Column("slot", String(24), nullable=False),
    Column("reason", String(500), nullable=False, server_default=""),
    Column("actor", String(48), nullable=False),
    Column("created_at", BigInteger, nullable=False),
    UniqueConstraint("case_id", "mass", "slot", name="uq_withdrawals_case_pair"),
)
