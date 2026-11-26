from time import time

from fastapi import HTTPException
from sqlalchemy import insert, select
from sqlalchemy.exc import IntegrityError

from src.constants.job_state import JobState
from src.domain.withdrawals import (
    pair_dicts,
    pairs_from_case_codes,
    queried_codes,
    queried_pairs,
    withdrawal_pair,
)
from src.models.cases import cases
from src.models.withdrawals import withdrawals
from . import audit, cases as case_service


def serialize(row):
    entry = dict(row)
    mass = entry.get("mass")
    slot = entry.get("slot")
    if entry.get("id") is not None:
        entry["code"] = f"WD-{int(entry['id']):08d}"
    entry.update({
        "mass_band": mass,
        "weight": mass,
        "weight_band": mass,
        "weight_tier": mass,
        "slot_band": slot,
        "slot_width": slot,
        "slot_width_band": slot,
        "slot_width_tier": slot,
        "effective_at": entry.get("created_at"),
        "registered_at": entry.get("created_at"),
        "withdrawn_at": entry.get("created_at"),
        "timestamp": entry.get("created_at"),
        "registered_by": entry.get("actor"),
        "operator": entry.get("actor"),
        "重量档": mass,
        "槽宽档": slot,
        "pair": {"mass": mass, "slot": slot},
        "bands": {"mass": mass, "slot": slot},
        "withdrawn_pair": [mass, slot],
        "status": "withdrawn",
        "effective": True,
    })
    return entry


def get(db, withdrawal_id):
    row = db.execute(
        select(withdrawals).where(withdrawals.c.id == withdrawal_id)
    ).mappings().first()
    if row is None:
        raise HTTPException(404, "撤回登记不存在")
    return serialize(row)


def list_for_case(db, case_id, lock=False):
    statement = select(withdrawals).where(withdrawals.c.case_id == case_id).order_by(withdrawals.c.id)
    if lock:
        statement = statement.with_for_update()
    rows = db.execute(statement).mappings().all()
    return [serialize(row) for row in rows]


def list_for_cases(db, case_ids):
    ids = list(case_ids)
    if not ids:
        return []
    rows = db.execute(
        select(withdrawals)
        .where(withdrawals.c.case_id.in_(ids))
        .order_by(withdrawals.c.id)
    ).mappings().all()
    return [serialize(row) for row in rows]


def list_all(db, limit=100):
    rows = db.execute(
        select(withdrawals).order_by(withdrawals.c.id.desc()).limit(limit)
    ).mappings().all()
    return [serialize(row) for row in rows]


def lock_case(db, case_id):
    """Serialize withdrawal registration against sign-off and hand-off."""
    return db.execute(
        select(cases.c.id).where(cases.c.id == case_id).with_for_update()
    ).first()


def register(db, case_id, data, actor):
    case_service.get(db, case_id)
    lock_case(db, case_id)

    existing = db.execute(
        select(withdrawals).where(
            withdrawals.c.case_id == case_id,
            withdrawals.c.mass == data.mass,
            withdrawals.c.slot == data.slot,
        )
    ).mappings().first()
    if existing is not None:
        raise HTTPException(409, "该重量档与槽宽档的实测依据已经撤回")

    now = int(time())
    try:
        change = db.execute(insert(withdrawals).values(
            case_id=case_id,
            mass=data.mass,
            slot=data.slot,
            reason=data.reason,
            actor=actor,
            created_at=now,
        ))
    except IntegrityError as exc:
        raise HTTPException(409, "该重量档与槽宽档的实测依据已经撤回") from exc

    withdrawal_id = change.inserted_primary_key[0]
    audit.record(db, "withdraw_basis", actor, "withdrawal", withdrawal_id)
    entry = get(db, withdrawal_id)
    all_pairs = [
        {"mass": item["mass"], "slot": item["slot"]}
        for item in list_for_case(db, case_id)
    ]
    entry["withdrawn_pairs"] = all_pairs
    entry["case_withdrawn_pairs"] = all_pairs
    return entry


def _value(item, key):
    if isinstance(item, dict):
        return item.get(key)
    return getattr(item, key, None)


def validity_for_run(run, case_withdrawals, case_payload=None):
    case_id = run.get("case_id") if isinstance(run, dict) else getattr(run, "case_id", None)
    related = [item for item in case_withdrawals if _value(item, "case_id") == case_id]
    result = run.get("result") if isinstance(run, dict) else getattr(run, "result", None)
    queried = queried_pairs(result)
    queried |= pairs_from_case_codes(case_payload, queried_codes(result))
    conflicts = [
        item for item in related
        if tuple(withdrawal_pair(item)) in queried
    ]
    pairs = [
        {"mass": pair[0], "slot": pair[1]}
        for item in conflicts
        for pair in [withdrawal_pair(item)]
    ]
    queried_list = pair_dicts(queried)
    valid = not conflicts
    status = run.get("status") if isinstance(run, dict) else getattr(run, "status", None)
    is_done = status == JobState.DONE
    if conflicts:
        certificate_status = "invalid"
        certificate_state = "invalidated"
    elif is_done:
        certificate_status = "valid"
        certificate_state = "valid"
    else:
        certificate_status = str(status)
        certificate_state = str(status)
    invalidated_at = min((_value(item, "created_at") for item in conflicts if _value(item, "created_at")), default=None)

    return {
        "valid": valid,
        "is_valid": valid,
        "certificate_valid": valid,
        "evidence_valid": valid,
        "handoff_allowed": valid and is_done,
        "can_handoff": valid and is_done,
        "invalid": not valid,
        "invalidated": not valid,
        "revoked": not valid,
        "withdrawn": not valid,
        "validity": "valid" if valid else "withdrawn_basis",
        "validity_status": "valid" if valid else "invalid",
        "validity_state": certificate_state,
        "certificate_status": certificate_status,
        "certificate_state": certificate_state,
        "evidence_status": certificate_status,
        "proof_status": certificate_status,
        "capacity_status": certificate_status,
        "revocation_status": "revoked" if conflicts else "active",
        "withdrawal_status": "withdrawn" if conflicts else "none",
        "state": "invalidated" if conflicts else str(status),
        "lifecycle_status": "invalidated" if conflicts else str(status),
        "invalidated_at": invalidated_at,
        "revoked_at": invalidated_at,
        "withdrawn_at": invalidated_at,
        "withdrawal": conflicts[0] if conflicts else None,
        "withdrawals": conflicts,
        "withdrawn_bases": conflicts,
        "withdrawn_pairs": pairs,
        "revoked_pairs": pairs,
        "queried_pairs": queried_list,
    }


def annotate_run(db, run):
    rows = list_for_case(db, run["case_id"])
    payload = db.scalar(select(cases.c.payload).where(cases.c.id == run["case_id"]))
    run.update(validity_for_run(run, rows, payload))
    return run


def annotate_runs(db, entries):
    case_ids = {entry["case_id"] for entry in entries}
    rows = list_for_cases(db, case_ids)
    payload_rows = db.execute(
        select(cases.c.id, cases.c.payload).where(cases.c.id.in_(case_ids))
    ).mappings().all() if case_ids else []
    payloads = {row["id"]: row["payload"] for row in payload_rows}
    for entry in entries:
        entry.update(validity_for_run(entry, rows, payloads.get(entry["case_id"])))
    return entries


def conflicts_for_run(db, run, lock=False):
    rows = list_for_case(db, run["case_id"], lock=lock)
    payload = db.scalar(select(cases.c.payload).where(cases.c.id == run["case_id"]))
    return validity_for_run(run, rows, payload)["withdrawals"]


# Common verb aliases used by callers/tests.
create = register
register_withdrawal = register
withdraw = register
withdraw_basis = register
revoke = register
revoke_basis = register
invalidate_for_run = conflicts_for_run
