from fastapi import APIRouter, Depends, HTTPException, status

from backend.dependencies import get_authorized_project, get_current_user, require_project_roles
from backend.schemas import ReviewCreate, ReviewStatusUpdate
from database.audit_log import log_event
from database.review_store import list_reviews, save_review, update_review_status


router = APIRouter(prefix="/projects/{project_id}/reviews", tags=["review"])


@router.get("", summary="List reviews for an authorized project")
def get_reviews(
    project_id: int,
    limit: int = 20,
    current_user: dict = Depends(get_current_user),
    project: dict = Depends(get_authorized_project),
):
    return list_reviews(
        limit=max(1, min(limit, 200)),
        user_id=current_user["id"],
        project_id=project["id"],
    )


@router.post("", status_code=201, summary="Create a project review (admin or architect)")
def create_review(
    project_id: int,
    request: ReviewCreate,
    current_user: dict = Depends(get_current_user),
    project: dict = Depends(get_authorized_project),
):
    require_project_roles(project, "admin", "architect")
    try:
        review = save_review(
            request.question,
            request.answer,
            request.confidence,
            request.review_status,
            user_id=current_user["id"],
            project_id=project["id"],
        )
    except PermissionError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "review_forbidden", "message": "Your role cannot submit reviews."},
        ) from None
    log_event(
        "REVIEW",
        user_id=current_user["id"],
        username=current_user["username"],
        project_id=project["id"],
        details={"client": "api", "review_status": request.review_status},
    )
    return review


@router.patch("/{review_id}", summary="Update a review status (admin or architect)")
def update_review(
    project_id: int,
    review_id: str,
    request: ReviewStatusUpdate,
    current_user: dict = Depends(get_current_user),
    project: dict = Depends(get_authorized_project),
):
    require_project_roles(project, "admin", "architect")
    try:
        review = update_review_status(
            review_id,
            request.review_status,
            user_id=current_user["id"],
            project_id=project["id"],
        )
    except PermissionError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "review_forbidden", "message": "Your role cannot update reviews."},
        ) from None
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "review_not_found", "message": "Review not found in this project."},
        ) from None
    log_event(
        "REVIEW",
        user_id=current_user["id"],
        username=current_user["username"],
        project_id=project["id"],
        details={"client": "api", "review_id": review_id, "review_status": request.review_status},
    )
    return review