import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

from backend.routes import (
    audit,
    auth,
    comparison,
    documents,
    exports,
    projects,
    query,
    relationships,
    review,
    traceability,
)
from database.access_control import AuthorizationError


logger = logging.getLogger(__name__)

app = FastAPI(
    title="AutoArch-AI API",
    description="Project-scoped architecture document processing and analysis services.",
    version="1.0.0",
)


def _error(status_code, code, message, headers=None):
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message}},
        headers=headers,
    )


@app.exception_handler(HTTPException)
async def http_error_handler(_request: Request, exception: HTTPException):
    detail = exception.detail
    if isinstance(detail, dict):
        code = str(detail.get("code", "request_error"))
        message = str(detail.get("message", "The request could not be completed."))
    else:
        code = "request_error"
        message = str(detail)
    return _error(exception.status_code, code, message, exception.headers)


@app.exception_handler(AuthorizationError)
async def authorization_error_handler(_request: Request, exception: AuthorizationError):
    return _error(403, "forbidden", str(exception))


@app.exception_handler(RequestValidationError)
async def validation_error_handler(_request: Request, _exception: RequestValidationError):
    return _error(400, "invalid_request", "Request data did not match the expected schema.")


@app.exception_handler(ValueError)
async def value_error_handler(_request: Request, exception: ValueError):
    return _error(400, "invalid_request", str(exception))


@app.exception_handler(Exception)
async def unexpected_error_handler(_request: Request, exception: Exception):
    logger.exception("Unhandled API exception", exc_info=exception)
    return _error(500, "internal_error", "An unexpected server error occurred.")


@app.get("/health", tags=["health"], summary="Check API health")
def health():
    return {"status": "ok", "service": "AutoArch-AI"}


app.include_router(auth.router)
app.include_router(projects.router)
app.include_router(documents.router)
app.include_router(query.router)
app.include_router(traceability.router)
app.include_router(relationships.router)
app.include_router(comparison.router)
app.include_router(review.router)
app.include_router(audit.router)
app.include_router(exports.router)