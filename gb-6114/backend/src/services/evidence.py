from sqlalchemy import select

from src.models.cases import cases
from src.models.runs import runs
from . import reviews, runs as run_service, withdrawals


def lock_certificate(db, run_id):
    """Lock run then parent case, matching worker/sign lock order."""
    locked = db.execute(
        select(runs.c.id, runs.c.case_id, runs.c.status)
        .where(runs.c.id == run_id)
        .with_for_update()
    ).mappings().first()
    if locked is None:
        return None
    db.execute(
        select(cases.c.id).where(cases.c.id == locked["case_id"]).with_for_update()
    ).first()
    return locked


def bundle(db, run_id, strict=False):
    if strict:
        locked = lock_certificate(db, run_id)
        if locked is None:
            run_service.get(db, run_id)  # Raises the canonical 404.
    run = run_service.get(db, run_id)
    if strict:
        # A locking read is a current read even under MySQL REPEATABLE READ.
        rows = withdrawals.list_for_case(db, run["case_id"], lock=True)
        payload = db.scalar(select(cases.c.payload).where(cases.c.id == run["case_id"]))
        run.update(withdrawals.validity_for_run(run, rows, payload))
        run["conflicts"] = run["withdrawals"]
    review = reviews.get(db, run_id)
    return {**run, "review": review}
