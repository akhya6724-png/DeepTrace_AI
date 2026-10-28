"""Pydantic response models (Pydantic v2)."""

from typing import Any, Literal

from pydantic import BaseModel, Field

Strength = Literal["informational", "weak", "moderate"]
Category = Literal[
    "no_strong_indicators_found",
    "inconclusive",
    "potential_manipulation_indicators",
    "analysis_incomplete",
]


class ErrorResponse(BaseModel):
    detail: str


class Finding(BaseModel):
    id: str
    source: str = Field(description="Module that produced the finding (metadata, ela, provenance, ...).")
    title: str
    strength: Strength = Field(description="informational | weak | moderate. Never 'proof'.")
    observation: str = Field(description="What was observed.")
    method: str = Field(description="How it was measured.")
    why_it_matters: str
    alternative_explanations: list[str] = Field(default_factory=list)
    additional_evidence_needed: list[str] = Field(default_factory=list)
    evidence: dict[str, Any] = Field(default_factory=dict)


class ImageInfo(BaseModel):
    original_filename: str
    format: str
    mime_type: str
    width: int
    height: int
    megapixels: float
    color_mode: str
    frame_count: int = 1
    file_size_bytes: int
    sha256: str


class MetadataResult(BaseModel):
    status: str
    error: str | None = None
    exif_present: bool = False
    exif: dict[str, Any] = Field(default_factory=dict)
    summary: dict[str, Any] = Field(default_factory=dict)
    gps: dict[str, Any] = Field(default_factory=dict)
    container_info: dict[str, Any] = Field(default_factory=dict)
    flags: dict[str, Any] = Field(default_factory=dict)
    findings: list[Finding] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


class ELAResult(BaseModel):
    status: str
    error: str | None = None
    method: str | None = None
    jpeg_quality: int | None = None
    source_format: str | None = None
    interpretability: str | None = None
    difference_statistics: dict[str, Any] | None = None
    block_statistics: dict[str, Any] | None = None
    visualization: dict[str, Any] | None = None
    evidence_url: str | None = None
    explanation: str = ""
    limitations: list[str] = Field(default_factory=list)
    findings: list[Finding] = Field(default_factory=list)


class Indicator(BaseModel):
    name: str
    value: Any
    method: str
    explanation: str
    limitations: list[str] = Field(default_factory=list)


class AIDetectionResult(BaseModel):
    status: str = Field(description="ok | unavailable | error")
    prediction: str | None = None
    confidence: float | None = Field(default=None, description="Model-reported score; NOT a calibrated probability.")
    method: str | None = None
    detector: dict[str, Any] | None = None
    error: str | None = None
    explanation: str = ""
    limitations: list[str] = Field(default_factory=list)


class ProvenanceResult(BaseModel):
    status: str = Field(description="no_credentials_detected | credentials_detected_unverified | error")
    credentials_detected: bool = False
    verification: str = Field(description="not_applicable | not_performed | verified")
    container: str | None = None
    evidence: dict[str, Any] = Field(default_factory=dict)
    explanation: str = ""
    limitations: list[str] = Field(default_factory=list)


class CheckStatus(BaseModel):
    name: str
    status: str
    detail: str | None = None


class OverallAssessment(BaseModel):
    category: Category
    summary: str
    rationale: list[str] = Field(default_factory=list)
    findings: list[Finding] = Field(default_factory=list)
    checks: list[CheckStatus] = Field(default_factory=list)
    recommended_next_steps: list[str] = Field(default_factory=list)
    scoring_note: str = ""


class EvidenceItem(BaseModel):
    name: str
    description: str
    url: str
    content_type: str


class AnalysisResponse(BaseModel):
    analysis_id: str
    created_at: str
    status: Literal["completed", "partial"]
    image_info: ImageInfo
    metadata: MetadataResult
    ela: ELAResult
    indicators: list[Indicator] = Field(default_factory=list)
    ai_detection: AIDetectionResult
    provenance: ProvenanceResult
    overall_assessment: OverallAssessment
    limitations: list[str] = Field(default_factory=list)
    evidence: list[EvidenceItem] = Field(default_factory=list)
    report_url: str | None = None
    warnings: list[str] = Field(default_factory=list)


class AnalysisSummary(BaseModel):
    analysis_id: str
    created_at: str
    status: str
    assessment_category: str | None = None
    original_filename: str | None = None
    format: str | None = None
    width: int | None = None
    height: int | None = None
    report_url: str | None = None


class AnalysisListResponse(BaseModel):
    items: list[AnalysisSummary]
    total: int
    limit: int
    offset: int


class DeleteResponse(BaseModel):
    analysis_id: str
    deleted: bool


class RootResponse(BaseModel):
    name: str
    version: str
    status: str
    docs_url: str


class HealthResponse(BaseModel):
    status: str
    service: str


class ApiHealthResponse(BaseModel):
    status: str
    version: str
    services: dict[str, str]
