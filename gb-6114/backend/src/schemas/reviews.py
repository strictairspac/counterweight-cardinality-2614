from pydantic import BaseModel, Field, field_validator


class ReviewInput(BaseModel):
    note: str = Field(min_length=3, max_length=500)

    @field_validator("note")
    @classmethod
    def check_note(cls, note):
        if len(note.strip()) < 3:
            raise ValueError("复核意见至少需要三个字符")
        return note.strip()


class ReviewEntry(ReviewInput):
    run_id: int
    actor: str
    created_at: int
    valid: bool = True
    certificate_valid: bool = True
    invalidated: bool = False
    revoked: bool = False
    signature_preserved: bool = True
    withdrawals: list[dict] = Field(default_factory=list)
    withdrawn_pairs: list[dict] = Field(default_factory=list)
