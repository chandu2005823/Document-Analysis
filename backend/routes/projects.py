from fastapi import APIRouter, Depends, HTTPException, status

from backend.dependencies import get_authorized_project, get_current_user
from backend.schemas import ProjectCreate, ProjectResponse
from database.access_control import AuthorizationError, create_project, list_user_projects
from database.audit_log import log_event


router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("", response_model=list[ProjectResponse], summary="List projects accessible to the user")
def list_projects(current_user: dict = Depends(get_current_user)):
    return list_user_projects(current_user["id"])


@router.post("", response_model=ProjectResponse, status_code=201, summary="Create a project (admin only)")
def create_project_endpoint(
    request: ProjectCreate,
    current_user: dict = Depends(get_current_user),
):
    try:
        project = create_project(current_user["id"], request.name)
    except AuthorizationError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "role_forbidden", "message": "Only admins can create projects."},
        ) from None
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "invalid_project", "message": str(error)},
        ) from None
    log_event(
        "PROJECT_CREATED",
        user_id=current_user["id"],
        username=current_user["username"],
        project_id=project["id"],
        details={"client": "api"},
    )
    return project


@router.get("/{project_id}", response_model=ProjectResponse, summary="Get an authorized project")
def get_project(project: dict = Depends(get_authorized_project)):
    return {"id": project["id"], "name": project["name"], "role": project["role"]}