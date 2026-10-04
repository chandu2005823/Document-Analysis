from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from backend.dependencies import get_authorized_project, get_current_user, require_project_roles
from backend.schemas import DocumentResponse
from database.access_control import AuthorizationError, list_project_documents
from database.audit_log import log_event
from frontend.document_processor import process_uploaded_pdf


router = APIRouter(prefix="/projects/{project_id}/documents", tags=["documents"])


class _UploadedDocument:
    def __init__(self, name, content):
        self.name = name
        self._content = content

    def getbuffer(self):
        return memoryview(self._content)


def _document_response(record):
    return {
        "document_id": record["document_id"],
        "project_id": record["project_id"],
        "filename": record["filename"],
        "version": record["version"],
        "pages": record["page_count"],
        "chunks": record["chunk_count"],
        "traceability_count": record["traceability_count"],
        "relationship_count": record.get("relationship_count", 0),
        "upload_timestamp": record.get("upload_timestamp"),
    }


@router.post("", response_model=DocumentResponse, status_code=201, summary="Upload and process a project PDF")
def upload_document(
    project_id: int,
    file: UploadFile = File(..., description="AUTOSAR PDF document"),
    current_user: dict = Depends(get_current_user),
    project: dict = Depends(get_authorized_project),
):
    require_project_roles(project, "admin", "architect")
    filename = Path(file.filename or "").name
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "invalid_file", "message": "Only PDF uploads are supported."},
        )
    try:
        payload = file.file.read()
        result = process_uploaded_pdf(
            _UploadedDocument(filename, payload),
            user_id=current_user["id"],
            project_id=project_id,
        )
    except AuthorizationError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "project_forbidden", "message": "You are not authorized to upload to this project."},
        ) from None
    except PermissionError as error:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "upload_forbidden", "message": str(error)},
        ) from None
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "invalid_document", "message": str(error)},
        ) from None
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "document_not_found", "message": "The uploaded document could not be read."},
        ) from None

    log_event(
        "DOCUMENT_UPLOAD",
        document_name=result["filename"],
        status="success",
        user_id=current_user["id"],
        username=current_user["username"],
        project_id=project_id,
        document_id=result["document_id"],
        details={"client": "api", "version": result["version"]},
    )
    return {
        **result,
        "project_id": project_id,
        "traceability_count": result["traceability_records"],
        "relationship_count": result["relationship_records"],
        "upload_timestamp": result["version_info"].get("upload_timestamp"),
    }


@router.get("", response_model=list[DocumentResponse], summary="List documents in an authorized project")
def list_documents(
    project_id: int,
    current_user: dict = Depends(get_current_user),
    project: dict = Depends(get_authorized_project),
):
    try:
        documents = list_project_documents(current_user["id"], project["id"])
    except AuthorizationError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "project_forbidden", "message": "You are not authorized for this project."},
        ) from None
    return [_document_response(document) for document in documents]