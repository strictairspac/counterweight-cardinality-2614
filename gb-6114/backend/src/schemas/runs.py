from pydantic import BaseModel, Field

from src.constants.job_state import JobState


class RunInput(BaseModel):
    parameter: int = Field(strict=True, ge=1)


class RunEntry(BaseModel):
    id: int
    case_id: int
    case_title: str
    status: JobState
    parameter: int
    actor: str
    created_at: int
    finished_at: int | None
    result: dict | None
    failure: str | None
    digest: str | None

    # Validity is computed from immutable results plus append-only withdrawals.
    valid: bool = True
    is_valid: bool = True
    certificate_valid: bool = True
    evidence_valid: bool = True
    handoff_allowed: bool = True
    can_handoff: bool = True
    invalid: bool = False
    invalidated: bool = False
    revoked: bool = False
    withdrawn: bool = False
    validity: str = "valid"
    validity_status: str = "valid"
    validity_state: str = "valid"
    state: str = "done"
    lifecycle_status: str = "done"
    certificate_status: str = "valid"
    certificate_state: str = "valid"
    evidence_status: str = "valid"
    proof_status: str = "valid"
    capacity_status: str = "valid"
    revocation_status: str = "active"
    withdrawal_status: str = "none"
    invalidated_at: int | None = None
    revoked_at: int | None = None
    withdrawn_at: int | None = None
    withdrawal: dict | None = None
    withdrawals: list[dict] = Field(default_factory=list)
    withdrawn_bases: list[dict] = Field(default_factory=list)
    withdrawn_pairs: list[dict] = Field(default_factory=list)
    revoked_pairs: list[dict] = Field(default_factory=list)
    queried_pairs: list[dict] = Field(default_factory=list)
