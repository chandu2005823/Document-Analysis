from typing import Any, Literal

from pydantic import BaseModel, Field


class TokenRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1)


class TokenResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int


class UserResponse(BaseModel):
    id: int
    username: str
    role: str


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)


class ProjectResponse(BaseModel):
    id: int
    name: str
    role: str


class DocumentResponse(BaseModel):
    document_id: str
    project_id: int
    filename: str
    version: int
    pages: int
    chunks: int
    traceability_count: int
    relationship_count: int
    upload_timestamp: str | None = None


class QueryRequest(BaseModel):
    question: str = Field(min_length=1, max_length=10000)


class QueryResponse(BaseModel):
    answer: str
    retrieval_confidence: dict[str, Any]
    grounding: dict[str, Any]
    sources: list[dict[str, Any]]
    primary_source: dict[str, Any] | None
    project_id: int
    document_id: str | None


class GraphNode(BaseModel):
    id: str
    label: str


class GraphEdge(BaseModel):
    id: int
    source: str
    target: str
    relationship: str
    page: int | str | None = None
    project_id: int | None = None
    document_id: str | None = None


class RelationshipGraphResponse(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]


class ReviewCreate(BaseModel):
    question: str = Field(min_length=1, max_length=10000)
    answer: str = Field(min_length=1, max_length=30000)
    confidence: dict[str, Any] = Field(default_factory=dict)
    review_status: Literal["approved", "needs_review"]


class ReviewStatusUpdate(BaseModel):
    review_status: Literal["approved", "needs_review"]


class CompareRequest(BaseModel):
    baseline_document_id: str = Field(min_length=1, max_length=200)
    current_document_id: str = Field(min_length=1, max_length=200)


class CompareResponse(BaseModel):
    added: list[dict[str, Any]]
    removed: list[dict[str, Any]]
    unchanged: list[dict[str, Any]]


class ErrorBody(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    error: ErrorBody