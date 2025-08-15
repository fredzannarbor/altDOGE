"""
Data models for CFR Document Analyzer.

Defines core data structures for documents, analyses, and sessions.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum


class RegulationCategory(Enum):
    """Regulation categorization types."""
    SR = "SR"  # Statutorily Required
    NSR = "NSR" # Not Statutorily Required (or Non-Statutorily Required, depending on exact meaning)
    NRAN = "NRAN" # Not Required But Agency Needs
    UNKNOWN = "UNKNOWN"


class SessionStatus(Enum):
    """Analysis session status types."""
    CREATED = "created"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Document:
    """Represents a CFR document with metadata and content."""
    document_number: str
    title: str
    agency_slug: str
    publication_date: Optional[str] = None
    cfr_citation: Optional[str] = None
    content: Optional[str] = None
    content_length: int = 0
    id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def __post_init__(self):
        """Validate document data after initialization."""
        if not self.document_number or not self.title:
            raise ValueError("Document number and title are required")
        
        if self.content:
            self.content_length = len(self.content)


@dataclass
class AnalysisResult:
    """Results from analyzing a single document."""
    document_id: int
    prompt_strategy: str
    category: Optional[RegulationCategory] = None
    statutory_references: List[str] = field(default_factory=list)
    reform_recommendations: List[str] = field(default_factory=list)
    justification: Optional[str] = None
    raw_response: Optional[str] = None
    token_usage: int = 0
    processing_time: float = 0.0
    success: bool = True
    error_message: Optional[str] = None
    id: Optional[int] = None
    created_at: Optional[datetime] = None

    def __post_init__(self):
        """Validate analysis result data after initialization."""
        if not self.success and not self.error_message:
            raise ValueError("Error message required when analysis unsuccessful")


@dataclass
class AnalysisSession:
    """Represents an analysis session configuration and state."""
    session_id: str
    agency_slugs: List[str]
    prompt_strategy: str
    document_limit: Optional[int] = None
    status: SessionStatus = SessionStatus.CREATED
    documents_processed: int = 0
    total_documents: int = 0
    created_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    def __post_init__(self):
        """Validate session data after initialization."""
        if not self.agency_slugs:
            raise ValueError("At least one agency slug is required")
        
        if self.documents_processed < 0:
            raise ValueError("Documents processed cannot be negative")
        
        if self.total_documents < 0:
            raise ValueError("Total documents cannot be negative")

    @property
    def progress_percentage(self) -> float:
        """Calculate progress as percentage."""
        if self.total_documents == 0:
            return 0.0
        return (self.documents_processed / self.total_documents) * 100


@dataclass
class DOGEAnalysis:
    """DOGE-specific analysis results with structured output."""
    category: RegulationCategory
    statutory_references: List[str]
    reform_recommendations: List[str]
    justification: str
    confidence_score: Optional[float] = None
    
    @classmethod
    def from_llm_response(cls, response_text: str) -> 'DOGEAnalysis':
        """
        Parse LLM response into structured DOGE analysis.
        
        Args:
            response_text: Raw LLM response text
            
        Returns:
            DOGEAnalysis object
        """
        # Basic parsing - will be enhanced in later tasks
        category = RegulationCategory.UNKNOWN
        statutory_refs = []
        recommendations = []
        justification = response_text
        
        # Simple keyword-based categorization for proof of concept
        response_lower = response_text.lower()
        if 'statutorily required' in response_lower or 'sr' in response_lower:
            category = RegulationCategory.STATUTORILY_REQUIRED
        elif 'not statutorily required' in response_lower or 'nsr' in response_lower:
            category = RegulationCategory.NOT_STATUTORILY_REQUIRED
        elif 'agency needs' in response_lower or 'nran' in response_lower:
            category = RegulationCategory.NOT_REQUIRED_AGENCY_NEEDS
        
        return cls(
            category=category,
            statutory_references=statutory_refs,
            reform_recommendations=recommendations,
            justification=justification
        )


@dataclass
class MetaAnalysis:
    """Meta-analysis results synthesizing multiple document analyses."""
    session_id: str
    key_patterns: List[str] = field(default_factory=list)
    strategic_themes: List[str] = field(default_factory=list)
    priority_actions: List[str] = field(default_factory=list)
    goal_alignment: Optional[str] = None
    implementation_roadmap: Optional[str] = None
    executive_summary: Optional[str] = None
    reform_opportunities: List[str] = field(default_factory=list)
    implementation_challenges: List[str] = field(default_factory=list)
    stakeholder_impact: Optional[str] = None
    resource_requirements: Optional[str] = None
    risk_assessment: Optional[str] = None
    quick_wins: List[str] = field(default_factory=list)
    long_term_strategy: Optional[str] = None
    processing_time: float = 0.0
    success: bool = True
    error_message: Optional[str] = None
    created_at: Optional[datetime] = None

    def __post_init__(self):
        """Validate meta-analysis data after initialization."""
        if not self.success and not self.error_message:
            raise ValueError("Error message required when meta-analysis unsuccessful")


@dataclass
class ExportConfig:
    """Configuration for exporting analysis results."""
    format: str  # json, csv, html
    include_raw_responses: bool = False
    include_metadata: bool = True
    group_by_agency: bool = True
    filename_prefix: Optional[str] = None