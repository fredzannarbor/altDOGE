"""
Data models for the CFR Agency Document Counter.

This module defines the core data structures used throughout the application
for representing agencies, document counts, and processing results.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional


@dataclass
class Agency:
    """Represents a federal agency with CFR information."""
    name: str
    slug: str
    cfr_citation: str
    parent_agency: str
    active: bool
    description: str

    def __post_init__(self):
        """Validate agency data after initialization."""
        if not self.name or not self.slug:
            raise ValueError("Agency name and slug are required")


@dataclass
class AgencyDocumentCount:
    """Represents document count results for a specific agency."""
    agency: Agency
    document_count: int
    last_updated: datetime
    query_successful: bool
    error_message: Optional[str] = None

    def __post_init__(self):
        """Validate document count data after initialization."""
        if self.document_count < 0:
            raise ValueError("Document count cannot be negative")
        if not self.query_successful and not self.error_message:
            raise ValueError("Error message required when query unsuccessful")


@dataclass
class CountingResults:
    """Represents the complete results of the document counting process."""
    total_agencies: int
    successful_queries: int
    failed_queries: int
    agencies_with_documents: int
    agencies_without_documents: int
    total_documents: int
    execution_time: float
    timestamp: datetime
    results: List[AgencyDocumentCount]

    def __post_init__(self):
        """Validate counting results after initialization."""
        if self.total_agencies != len(self.results):
            raise ValueError("Total agencies must match results length")
        if self.successful_queries + self.failed_queries != self.total_agencies:
            raise ValueError("Successful + failed queries must equal total agencies")

    @property
    def success_rate(self) -> float:
        """Calculate the success rate as a percentage."""
        if self.total_agencies == 0:
            return 0.0
        return (self.successful_queries / self.total_agencies) * 100

    def get_summary(self) -> str:
        """Generate a human-readable summary of the results."""
        return (
            f"Processed {self.total_agencies} agencies in {self.execution_time:.1f}s\n"
            f"Success rate: {self.success_rate:.1f}% "
            f"({self.successful_queries}/{self.total_agencies})\n"
            f"Agencies with documents: {self.agencies_with_documents}\n"
            f"Total documents found: {self.total_documents:,}"
        )