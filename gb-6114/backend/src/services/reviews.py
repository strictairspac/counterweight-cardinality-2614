from time import time

from fastapi import HTTPException
from sqlalchemy import insert, select
from sqlalchemy.exc import IntegrityError

from src.constants.job_state import JobState
from src.models.cases import cases
from src.models.reviews import reviews
from src.models.runs import runs
from . import audit, runs as run_service, withdrawals


def get(db, run_id):
    row = db.execute(select(reviews).where(reviews.c.run_id == run_id)).mappings().first()
    if row is None:
        return None
    review = dict(row)
    # Preserve the signature while exposing the current certificate validity.
    run = run_service.get(db, run_id)
    review.update({
        "valid": run["valid"],
        "certificate_valid": run["certificate_valid"],
        "invalidated": run["invalidated"],
        "revoked": run["revoked"],
        "signature_preserved": True,
        "withdrawals": run["withdrawals"],
        "withdrawn_pairs": run["withdrawn_pairs"],
    })
    return review


def sign(db, run_id, data, actor):
    # Keep the same run -> case lock order used by worker completion. The case
    # lock is also taken by withdrawal registration, making sign-off vs
    # withdrawal a linearizable race.
    locked_run = db.execute(
        select(runs.c.id, runs.c.case_id, runs.c.status, runs.c.result)
        .where(runs.c.id == run_id)
        .with_for_update()
    ).mappings().first()
    if locked_run is None:
        raise HTTPException(404, "执行批次不存在")

    db.execute(
        select(cases.c.id).where(cases.c.id == locked_run["case_id"]).with_for_update()
    ).first()

    if locked_run["status"] != JobState.DONE:
        raise HTTPException(409, "批次执行成功后才能签核")

    run = run_service.get(db, run_id)
    conflicts = withdrawals.conflicts_for_run(db, run, lock=True)
    if conflicts:
        pairs = "、".join(f"{item['mass']} / {item['slot']}" for item in conflicts)
        raise HTTPException(409, f"档位对 {pairs} 的实测依据已撤回，容量证明已失效，不能签核")

    try:
        db.execute(insert(reviews).values(run_id=run_id, note=data.note, actor=actor, created_at=int(time())))
    except IntegrityError as exc:
        raise HTTPException(409, "该批次已经签核") from exc
    audit.record(db, "review", actor, "run", run_id)
    return get(db, run_id)
