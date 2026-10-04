from fastapi import APIRouter, Depends

from backend.dependencies import get_authorized_project, get_current_user
from backend.schemas import RelationshipGraphResponse
from backend.services import get_project_graph_data, get_project_relationships


router = APIRouter(prefix="/projects/{project_id}/relationships", tags=["relationships"])


@router.get("", summary="List relationships from authorized project documents")
def list_relationships(
    project_id: int,
    source: str | None = None,
    relationship: str | None = None,
    target: str | None = None,
    current_user: dict = Depends(get_current_user),
    project: dict = Depends(get_authorized_project),
):
    return get_project_relationships(
        current_user["id"],
        project["id"],
        source=source,
        relationship=relationship,
        target=target,
    )


@router.get(
    "/graph",
    response_model=RelationshipGraphResponse,
    summary="Return graph-ready nodes and page-aware relationship edges",
)
def relationship_graph(
    project_id: int,
    current_user: dict = Depends(get_current_user),
    project: dict = Depends(get_authorized_project),
):
    return get_project_graph_data(current_user["id"], project["id"])