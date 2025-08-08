"""
CFR Agency Document Counter

A tool for counting Federal Register documents by CFR agency using the
Federal Register API.
"""

__version__ = "1.0.0"
__author__ = "CFR Agency Counter Team"
__description__ = "Count Federal Register documents by CFR agency"

from .models import Agency, AgencyDocumentCount, CountingResults
from .data_loader import AgencyDataLoader
from .api_client import FederalRegisterClient, FederalRegisterAPIError
from .document_counter import DocumentCounter
from .progress_tracker import ProgressTracker
from .report_generator import ReportGenerator
from .config import Config

__all__ = [
    'Agency',
    'AgencyDocumentCount', 
    'CountingResults',
    'AgencyDataLoader',
    'FederalRegisterClient',
    'FederalRegisterAPIError',
    'DocumentCounter',
    'ProgressTracker',
    'ReportGenerator',
    'Config'
]