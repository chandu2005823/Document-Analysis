from fastapi import APIRouter, Depends, HTTPException, status

from backend.dependencies import TOKEN_TTL_SECONDS, create_access_token, get_current_user
from backend.schemas import TokenRequest, TokenResponse, UserResponse
from database.access_control import authenticate_user
from database.audit_log import log_event


router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post(
    "/token",
    response_model=TokenResponse,
    summary="Exchange credentials for a short-lived bearer token",
)
def issue_token(request: TokenRequest):
    user = authenticate_user(request.username, request.password)
    if user is None:
        log_event(
            "LOGIN",
            username=request.username,
            status="denied",
            details={"reason": "invalid_credentials", "client": "api"},
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "invalid_credentials", "message": "Invalid username or password."},
            headers={"WWW-Authenticate": "Bearer"},
        )
    log_event(
        "LOGIN",
        username=user["username"],
        user_id=user["id"],
        status="success",
        details={"client": "api"},
    )
    return TokenResponse(
        access_token=create_access_token(user["id"]),
        expires_in=TOKEN_TTL_SECONDS,
    )


@router.get("/me", response_model=UserResponse, summary="Return the authenticated user")
def get_me(current_user: dict = Depends(get_current_user)):
    return current_user