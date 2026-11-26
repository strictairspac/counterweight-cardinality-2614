from fastapi import APIRouter, Depends, HTTPException, Response

from src.config.resources import engine
from src.constants.job_state import JobState
from src.controllers.access import identity, operator, reviewer
from src.controllers.workbench import new_review, register_withdrawal
from src.schemas.reviews import ReviewEntry, ReviewInput
from src.schemas.runs import RunEntry
from src.schemas.withdrawals import WithdrawalInput
from src.services import evidence, handoffs, reviews, runs
from src.utils.serial import canonical_json

router = APIRouter(prefix="/runs", tags=["Execution"])
handoff_router = APIRouter(tags=["Handoff"])
certificate_router = APIRouter(tags=["Certificates"])


@router.get("", response_model=list[RunEntry], dependencies=[Depends(identity)])
def list_runs():
    with engine.connect() as db:
        return runs.list_entries(db)


@router.get("/{run_id}", response_model=RunEntry, dependencies=[Depends(identity)])
def run_detail(run_id: int):
    with engine.connect() as db:
        return runs.get(db, run_id)


@router.get("/{run_id}/validity", dependencies=[Depends(identity)])
def run_validity(run_id: int):
    with engine.connect() as db:
        run = runs.get(db, run_id)
        return {
            key: run[key]
            for key in (
                "valid", "is_valid", "certificate_valid", "handoff_allowed",
                "invalid", "invalidated", "revoked", "validity", "validity_status",
                "certificate_status", "invalidated_at", "revoked_at", "withdrawn_at",
                "withdrawal", "withdrawals", "withdrawn_pairs",
                "revoked_pairs", "queried_pairs",
            )
        }


@router.get("/{run_id}/review", response_model=ReviewEntry | None, dependencies=[Depends(identity)])
def review_detail(run_id: int):
    with engine.connect() as db:
        runs.get(db, run_id)
        return reviews.get(db, run_id)


@router.post("/{run_id}/review", response_model=ReviewEntry, status_code=201)
def sign(run_id: int, form: ReviewInput, user=Depends(reviewer)):
    return new_review(run_id, form, user)


def _register_run_withdrawal(run_id, form, user):
    with engine.connect() as db:
        run = runs.get(db, run_id)
    return register_withdrawal(run["case_id"], form, user)


@router.post("/{run_id}/withdrawals", status_code=201, include_in_schema=False)
def withdraw_basis_for_run(run_id: int, form: WithdrawalInput, user=Depends(operator)):
    return _register_run_withdrawal(run_id, form, user)


@router.post("/{run_id}/withdraw-basis", status_code=201, include_in_schema=False)
def withdraw_basis_for_run_alias(run_id: int, form: WithdrawalInput, user=Depends(operator)):
    return _register_run_withdrawal(run_id, form, user)


@router.post("/{run_id}/revoke", status_code=201, include_in_schema=False)
def revoke_for_run_alias(run_id: int, form: WithdrawalInput, user=Depends(operator)):
    return _register_run_withdrawal(run_id, form, user)


def _export_response(run_id, *, strict):
    with engine.begin() as db:
        payload = evidence.bundle(db, run_id, strict=strict)
        if payload["status"] != JobState.DONE:
            raise HTTPException(409, "没有可导出的执行结果")

        invalid = not payload["valid"]
        if strict and invalid:
            pairs = "、".join(
                f"{item['mass']} / {item['slot']}" for item in payload["withdrawn_pairs"]
            )
            payload.update({
                "detail": f"档位对 {pairs} 的实测依据已撤回，该证明已失效，不能作为有效件交接",
                "handoff_allowed": False,
                "exported_as": "invalid_readback",
            })
            status_code = 409
        else:
            payload.update({
                "handoff_allowed": payload["valid"],
                "exported_as": "valid_handoff" if payload["valid"] else "marked_readback",
            })
            status_code = 200

        body = canonical_json(payload)
        filename = f"evidence-{run_id}.json"
        headers = {
            "Content-Disposition": f"attachment; filename={filename}",
            "X-Evidence-Valid": "true" if payload["valid"] else "false",
            "X-Handoff-Allowed": "true" if payload["handoff_allowed"] else "false",
        }
        return Response(
            content=body,
            status_code=status_code,
            media_type="application/json",
            headers=headers,
        )


@router.get("/{run_id}/export", dependencies=[Depends(identity)])
def export(run_id: int):
    # The canonical hand-off endpoint refuses an invalidated certificate.
    return _export_response(run_id, strict=True)


@router.get("/{run_id}/handoff", dependencies=[Depends(identity)], include_in_schema=False)
def handoff(run_id: int):
    return _export_response(run_id, strict=True)


@router.get("/{run_id}/bundle", dependencies=[Depends(identity)], include_in_schema=False)
def marked_bundle(run_id: int):
    # Append-only readback: original result and signature remain intact.
    return _export_response(run_id, strict=False)


@router.get("/{run_id}/evidence-bundle", dependencies=[Depends(identity)], include_in_schema=False)
def evidence_bundle(run_id: int):
    return _export_response(run_id, strict=False)


@handoff_router.get("/handoffs/{run_id}", dependencies=[Depends(identity)], include_in_schema=False)
def top_level_handoff(run_id: int):
    return _export_response(run_id, strict=True)


@handoff_router.get("/handoffs/{run_id}/decision", dependencies=[Depends(identity)], include_in_schema=False)
def top_level_handoff_decision(run_id: int):
    with engine.connect() as db:
        return handoffs.handoff_decision(db, run_id)


for prefix in ("/certificates", "/capacity-certificates", "/proofs"):
    certificate_router.add_api_route(
        prefix, list_runs, methods=["GET"], dependencies=[Depends(identity)], include_in_schema=False
    )
    certificate_router.add_api_route(
        f"{prefix}/{{run_id}}", run_detail, methods=["GET"],
        dependencies=[Depends(identity)], include_in_schema=False,
    )
    certificate_router.add_api_route(
        f"{prefix}/{{run_id}}/validity", run_validity, methods=["GET"],
        dependencies=[Depends(identity)], include_in_schema=False,
    )
    certificate_router.add_api_route(
        f"{prefix}/{{run_id}}/export", export, methods=["GET"],
        dependencies=[Depends(identity)], include_in_schema=False,
    )
    certificate_router.add_api_route(
        f"{prefix}/{{run_id}}/review", sign, methods=["POST"],
        status_code=201, include_in_schema=False,
    )
    certificate_router.add_api_route(
        f"{prefix}/{{run_id}}/withdrawals", withdraw_basis_for_run, methods=["POST"],
        status_code=201, include_in_schema=False,
    )
