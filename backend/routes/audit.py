from fastapi import APIRouter, Depends

from backend.dependencies import get_authorized_project, get_current_user
from database.audit_log import _sanitize, read_logs


router = APIRouter(prefix="/projects/{project_id}/audit", tags=["audit"])


@router.get("", summary="Read audit events visible to the authenticated project member")
def get_project_audit(
    project_id: int,
    limit: int = 50,
    current_user: dict = Depends(get_current_user),
    project: dict = Depends(get_authorized_project),
):
    return _sanitize(
        read_logs(
            limit=max(1, min(limit, 200)),
            user_id=current_user["id"],
            project_id=project["id"],
        )
    )