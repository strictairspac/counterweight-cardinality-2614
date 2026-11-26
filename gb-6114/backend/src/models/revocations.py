from .withdrawals import withdrawals

# The append-only withdrawal record also acts as the revocation ledger.
revocations = withdrawals

__all__ = ["withdrawals", "revocations"]
