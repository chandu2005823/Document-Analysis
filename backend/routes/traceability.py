from fastapi import APIRouter, Depends

from backend.dependencies import get_authorized_project, get_current_user
from backend.services import get_project_traceability


router = APIRouter(prefix="/projects/{project_id}/traceability", tags=["traceability"])


@router.get("", summary="List page-aware traceability for an authorized project")
def list_traceability(
    project_id: int,
    entity_type: str | None = None,
    search: str | None = None,
    current_user: dict = Depends(get_current_user),
    project: dict = Depends(get_authorized_project),
):
    return get_project_traceability(
        current_user["id"],
        project["id"],
        entity_type=entity_type,
        search=search,
    )