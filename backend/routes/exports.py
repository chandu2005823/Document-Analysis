from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response

from analysis.document_comparison import compare_entities
from backend.dependencies import get_authorized_project, get_current_user
from backend.export_utils import export_csv_bytes, export_json_bytes
from backend.services import (
    get_document_traceability,
    get_project_relationships,
    get_project_traceability,
)
from database.audit_log import log_event


router = APIRouter(prefix="/projects/{project_id}/exports", tags=["exports"])


def _csv_content(records):
    return export_csv_bytes(records).decode("utf-8")


@router.get("/{artifact}", summary="Export project analysis as JSON or CSV")
def export_project_data(
    project_id: int,
    artifact: Literal["traceability", "relationships", "comparison"],
    format: Literal["json", "csv"] = Query(default="json"),
    baseline_document_id: str | None = None,
    current_document_id: str | None = None,
    current_user: dict = Depends(get_current_user),
    project: dict = Depends(get_authorized_project),
):
    if artifact == "traceability":
        records = get_project_traceability(current_user["id"], project["id"])
    elif artifact == "relationships":
        records = get_project_relationships(current_user["id"], project["id"])
    elif artifact == "comparison":
        if not baseline_document_id or not current_document_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": "comparison_documents_required",
                    "message": "baseline_document_id and current_document_id are required for comparison exports.",
                },
            )
        try:
            _baseline, old_records = get_document_traceability(
                current_user["id"], project["id"], baseline_document_id
            )
            _current, new_records = get_document_traceability(
                current_user["id"], project["id"], current_document_id
            )
        except PermissionError:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"code": "document_forbidden", "message": "Both documents must belong to this project."},
            ) from None
        comparison = compare_entities(old_records, new_records)
        records = [
            {"change_type": change_type, **record}
            for change_type in ("added", "removed", "unchanged")
            for record in comparison[change_type]
        ]
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "invalid_export", "message": "Unsupported export type."},
        )

    log_event(
        "EXPORT",
        user_id=current_user["id"],
        username=current_user["username"],
        project_id=project["id"],
        details={"client": "api", "artifact": artifact, "format": format},
    )
    filename = f"{artifact}_{project['id']}.{format}"
    if format == "csv":
        return Response(
            content=_csv_content(records),
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    return Response(
        content=export_json_bytes(records, filename),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )