from fastapi import APIRouter, Depends

from src.config.resources import engine
from src.controllers.access import identity, operator
from src.controllers.workbench import register_withdrawal
from src.schemas.withdrawals import WithdrawalInput
from src.services import withdrawals

router = APIRouter(tags=["Withdrawals"])


@router.get("/withdrawals", dependencies=[Depends(identity)])
def all_withdrawals():
    with engine.connect() as db:
        return withdrawals.list_all(db)


@router.get("/withdrawals/{withdrawal_id}", dependencies=[Depends(identity)])
def withdrawal_detail(withdrawal_id: int):
    with engine.connect() as db:
        return withdrawals.get(db, withdrawal_id)


@router.post("/withdrawals", status_code=201)
def create_withdrawal(form: WithdrawalInput, user=Depends(operator)):
    if form.case_id is None:
        from fastapi import HTTPException
        raise HTTPException(422, "必须提供 case_id")
    return register_withdrawal(form.case_id, form, user)


@router.post("/withdraw", status_code=201, include_in_schema=False)
def withdraw_alias(form: WithdrawalInput, user=Depends(operator)):
    return create_withdrawal(form, user)


@router.post("/withdraw-basis", status_code=201, include_in_schema=False)
def withdraw_basis_alias(form: WithdrawalInput, user=Depends(operator)):
    return create_withdrawal(form, user)


@router.post("/withdraw-measurement", status_code=201, include_in_schema=False)
def withdraw_measurement_alias(form: WithdrawalInput, user=Depends(operator)):
    return create_withdrawal(form, user)


@router.post("/revoke", status_code=201, include_in_schema=False)
def revoke_alias(form: WithdrawalInput, user=Depends(operator)):
    return create_withdrawal(form, user)


@router.get("/basis-withdrawals", dependencies=[Depends(identity)], include_in_schema=False)
def all_basis_withdrawals():
    return all_withdrawals()


@router.post("/basis-withdrawals", status_code=201, include_in_schema=False)
def create_basis_withdrawal(form: WithdrawalInput, user=Depends(operator)):
    return create_withdrawal(form, user)


@router.get("/revocations", dependencies=[Depends(identity)], include_in_schema=False)
def all_revocations():
    return all_withdrawals()


@router.post("/revocations", status_code=201, include_in_schema=False)
def create_revocation(form: WithdrawalInput, user=Depends(operator)):
    return create_withdrawal(form, user)
