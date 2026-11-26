"""Handoff policy helpers.

A completed run is the system's capacity certificate. The original payload and
review are never mutated by a withdrawal; only the computed validity/handoff
decision changes.
"""

from fastapi import HTTPException

from src.constants.job_state import JobState
from . import evidence, runs, withdrawals


def can_handoff(db, run_id):
    run = runs.get(db, run_id)
    return run["status"] == JobState.DONE and run["valid"]


def handoff_decision(db, run_id):
    run = runs.get(db, run_id)
    return {
        "run_id": run_id,
        "case_id": run["case_id"],
        "can_handoff": run["status"] == JobState.DONE and run["handoff_allowed"],
        "valid": run["valid"],
        "withdrawn_pairs": run["withdrawn_pairs"],
        "withdrawals": run["withdrawals"],
    }


def require_handoff(db, run_id):
    payload = evidence.bundle(db, run_id, strict=True)
    if payload["status"] != JobState.DONE:
        raise HTTPException(409, "没有可导出的执行结果")
    if not payload["valid"]:
        pairs = "、".join(
            f"{item['mass']} / {item['slot']}" for item in payload["withdrawn_pairs"]
        )
        raise HTTPException(
            status_code=409,
            detail={
                "message": f"档位对 {pairs} 的实测依据已撤回，该证明已失效，不能作为有效件交接",
                "valid": False,
                "handoff_allowed": False,
                "withdrawn_pairs": payload["withdrawn_pairs"],
                "withdrawals": payload["withdrawals"],
                "review": payload["review"],
            },
        )
    return payload


# Vocabulary aliases.
can_transfer = can_handoff
handoff_allowed = can_handoff
require_valid_handoff = require_handoff
block_if_invalid = require_handoff
register = withdrawals.register
