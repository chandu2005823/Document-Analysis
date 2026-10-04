from fastapi import APIRouter, Depends, HTTPException, status

from analysis.document_comparison import compare_entities
from backend.dependencies import get_authorized_project, get_current_user, require_project_roles
from backend.schemas import CompareRequest, CompareResponse
from backend.services import get_document_traceability
from database.audit_log import log_event


router = APIRouter(prefix="/projects/{project_id}/compare", tags=["comparison"])


@router.post("", response_model=CompareResponse, summary="Compare two documents within one project")
def compare_project_documents(
    project_id: int,
    request: CompareRequest,
    current_user: dict = Depends(get_current_user),
    project: dict = Depends(get_authorized_project),
):
    require_project_roles(project, "admin", "architect")
    try:
        baseline, old_records = get_document_traceability(
            current_user["id"], project["id"], request.baseline_document_id
        )
        current, new_records = get_document_traceability(
            current_user["id"], project["id"], request.current_document_id
        )
    except PermissionError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "document_forbidden", "message": "Both documents must belong to this project."},
        ) from None
    comparison = compare_entities(old_records, new_records)
    log_event(
        "COMPARISON",
        document_name=f"{baseline['filename']} vs {current['filename']}",
        user_id=current_user["id"],
        username=current_user["username"],
        project_id=project["id"],
        document_id=current["document_id"],
        details={"client": "api"},
    )
    return comparison