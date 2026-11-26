from fastapi import APIRouter, Body, Depends

from src.config.resources import engine
from src.controllers.access import identity, operator
from src.controllers.workbench import new_case, new_run, register_withdrawal
from src.schemas.cases import CaseDetail, CaseEntry, CaseInput
from src.schemas.runs import RunEntry, RunInput
from src.schemas.withdrawals import WithdrawalInput
from src.services import cases, runs, withdrawals

router = APIRouter(prefix="/cases", tags=["Cases"])


@router.get("", response_model=list[CaseEntry], dependencies=[Depends(identity)])
def list_cases():
    with engine.connect() as db:
        return cases.list_entries(db)


@router.get("/{case_id}", response_model=CaseDetail, dependencies=[Depends(identity)])
def case_detail(case_id: int):
    with engine.connect() as db:
        entry = cases.get(db, case_id)
        records = withdrawals.list_for_case(db, case_id)
        entry["withdrawals"] = records
        entry["withdrawn_pairs"] = [
            {"mass": item["mass"], "slot": item["slot"]} for item in records
        ]
        entry["withdrawn"] = bool(records)
        entry["has_withdrawal"] = bool(records)
        entry["withdrawal_status"] = "withdrawn" if records else "none"
        return entry


@router.post("", response_model=CaseEntry, status_code=201)
def register(form: CaseInput, user=Depends(operator)):
    return new_case(form, user)


@router.get("/{case_id}/runs", response_model=list[RunEntry], dependencies=[Depends(identity)])
def case_runs(case_id: int):
    with engine.connect() as db:
        cases.get(db, case_id)
        return runs.list_for_case(db, case_id)


@router.get("/{case_id}/certificates", response_model=list[RunEntry], dependencies=[Depends(identity)], include_in_schema=False)
def case_certificates(case_id: int):
    return case_runs(case_id)


@router.post("/{case_id}/runs", response_model=RunEntry, status_code=202)
def schedule(case_id: int, form: RunInput, user=Depends(operator)):
    return new_run(case_id, form, user)


@router.get("/{case_id}/withdrawals", dependencies=[Depends(identity)])
def case_withdrawals(case_id: int):
    with engine.connect() as db:
        cases.get(db, case_id)
        return withdrawals.list_for_case(db, case_id)


@router.post("/{case_id}/withdrawals", status_code=201)
def withdraw_basis(case_id: int, form: WithdrawalInput, user=Depends(operator)):
    return register_withdrawal(case_id, form, user)


@router.post("/{case_id}/withdrawals/{mass}/{slot}", status_code=201, include_in_schema=False)
def withdraw_basis_path_pair(
    case_id: int,
    mass: str,
    slot: str,
    payload: dict | None = Body(default=None),
    user=Depends(operator),
):
    values = {**(payload or {}), "mass": mass, "slot": slot}
    return register_withdrawal(case_id, WithdrawalInput.model_validate(values), user)


for path in (
    "/{case_id}/pairs/{mass}/{slot}/withdraw",
    "/{case_id}/pair/{mass}/{slot}/withdraw",
    "/{case_id}/basis/withdraw/{mass}/{slot}",
):
    router.add_api_route(
        path,
        withdraw_basis_path_pair,
        methods=["POST"],
        status_code=201,
        dependencies=[Depends(operator)],
        include_in_schema=False,
    )

# Compatibility aliases for the same registration workflow.
for path in (
    "/{case_id}/withdrawal",
    "/{case_id}/withdraw",
    "/{case_id}/withdraw-pair",
    "/{case_id}/withdraw-basis",
    "/{case_id}/basis/withdraw",
    "/{case_id}/basis-withdrawal",
    "/{case_id}/basis-withdrawals",
    "/{case_id}/measurement-withdrawal",
    "/{case_id}/measurement-withdrawals",
    "/{case_id}/measurement-basis-withdrawals",
    "/{case_id}/withdrawn-pairs",
    "/{case_id}/revoked-pairs",
    "/{case_id}/revoke",
    "/{case_id}/revoke-pair",
    "/{case_id}/revocations",
):
    router.add_api_route(
        path,
        withdraw_basis,
        methods=["POST"],
        status_code=201,
        dependencies=[Depends(operator)],
        include_in_schema=False,
    )

for path in (
    "/{case_id}/withdrawal",
    "/{case_id}/basis-withdrawal",
    "/{case_id}/basis-withdrawals",
    "/{case_id}/measurement-withdrawal",
    "/{case_id}/measurement-withdrawals",
    "/{case_id}/measurement-basis-withdrawals",
    "/{case_id}/withdrawn-pairs",
    "/{case_id}/revoked-pairs",
    "/{case_id}/revocations",
):
    router.add_api_route(
        path,
        case_withdrawals,
        methods=["GET"],
        dependencies=[Depends(identity)],
        include_in_schema=False,
    )
