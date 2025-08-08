"""
Agency Data Loader for parsing and filtering agency information from CSV files.

This module handles loading agency data from the Federal Register agencies CSV file,
filtering for CFR agencies, and preparing data for document counting.
"""

import csv
import logging
from pathlib import Path
from typing import List, Dict, Any

from .models import Agency


logger = logging.getLogger(__name__)


class AgencyDataLoader:
    """Loads and processes agency data from CSV files."""
    
    def __init__(self):
        """Initialize the agency data loader."""
        self.agencies: List[Agency] = []
    
    def load_agencies(self, file_path: str) -> List[Agency]:
        """
        Load agencies from a CSV file.
        
        Args:
            file_path: Path to the agencies CSV file
            
        Returns:
            List of Agency objects
            
        Raises:
            FileNotFoundError: If the CSV file doesn't exist
            ValueError: If the CSV file has invalid format or data
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"Agencies file not found: {file_path}")
        
        logger.info(f"Loading agencies from {file_path}")
        
        agencies = []
        required_columns = {'active', 'cfr_citation', 'parent_agency_name', 'agency_name', 'description'}
        
        try:
            with open(file_path, 'r', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                
                # Validate CSV headers
                if not required_columns.issubset(set(reader.fieldnames or [])):
                    missing = required_columns - set(reader.fieldnames or [])
                    raise ValueError(f"Missing required columns in CSV: {missing}")
                
                for row_num, row in enumerate(reader, start=2):  # Start at 2 for header
                    try:
                        agency = self._parse_agency_row(row)
                        if agency:
                            agencies.append(agency)
                    except Exception as e:
                        logger.warning(f"Skipping invalid row {row_num}: {e}")
                        continue
        
        except Exception as e:
            logger.error(f"Error reading CSV file: {e}")
            raise ValueError(f"Failed to parse CSV file: {e}")
        
        logger.info(f"Loaded {len(agencies)} agencies from CSV")
        self.agencies = agencies
        return agencies
    
    def _parse_agency_row(self, row: Dict[str, Any]) -> Agency:
        """
        Parse a single CSV row into an Agency object.
        
        Args:
            row: Dictionary representing a CSV row
            
        Returns:
            Agency object or None if row should be skipped
            
        Raises:
            ValueError: If row data is invalid
        """
        # Skip rows with empty agency names
        agency_name = row.get('agency_name', '').strip()
        if not agency_name:
            return None
        
        # Parse active status
        active_str = row.get('active', '').strip()
        if active_str not in ('0', '1'):
            raise ValueError(f"Invalid active status: {active_str}")
        active = active_str == '1'
        
        # Generate slug from agency name
        slug = self._generate_slug(agency_name)
        
        # Extract other fields
        cfr_citation = row.get('cfr_citation', '').strip()
        parent_agency = row.get('parent_agency_name', '').strip()
        description = row.get('description', '').strip()
        
        return Agency(
            name=agency_name,
            slug=slug,
            cfr_citation=cfr_citation,
            parent_agency=parent_agency,
            active=active,
            description=description
        )
    
    def _generate_slug(self, agency_name: str) -> str:
        """
        Generate a URL-friendly slug from an agency name.
        
        Args:
            agency_name: The agency name to convert
            
        Returns:
            URL-friendly slug
        """
        # Convert to lowercase and replace spaces/special chars with hyphens
        slug = agency_name.lower()
        slug = ''.join(c if c.isalnum() else '-' for c in slug)
        # Remove multiple consecutive hyphens and strip leading/trailing hyphens
        slug = '-'.join(part for part in slug.split('-') if part)
        return slug
    
    def filter_cfr_agencies(self, agencies: List[Agency] = None) -> List[Agency]:
        """
        Filter agencies to only include those with CFR citations.
        
        Args:
            agencies: List of agencies to filter (uses loaded agencies if None)
            
        Returns:
            List of agencies with CFR citations
        """
        if agencies is None:
            agencies = self.agencies
        
        cfr_agencies = [agency for agency in agencies if agency.cfr_citation]
        
        logger.info(f"Filtered to {len(cfr_agencies)} agencies with CFR citations")
        return cfr_agencies
    
    def get_active_agencies(self, agencies: List[Agency] = None) -> List[Agency]:
        """
        Filter agencies to only include active ones.
        
        Args:
            agencies: List of agencies to filter (uses loaded agencies if None)
            
        Returns:
            List of active agencies
        """
        if agencies is None:
            agencies = self.agencies
        
        active_agencies = [agency for agency in agencies if agency.active]
        
        logger.info(f"Filtered to {len(active_agencies)} active agencies")
        return active_agencies
    
    def get_cfr_active_agencies(self, file_path: str = None) -> List[Agency]:
        """
        Load agencies and filter for active agencies with CFR citations.
        
        Args:
            file_path: Path to agencies CSV file (if not already loaded)
            
        Returns:
            List of active agencies with CFR citations
        """
        if file_path and not self.agencies:
            self.load_agencies(file_path)
        
        # Apply both filters
        cfr_agencies = self.filter_cfr_agencies()
        active_cfr_agencies = self.get_active_agencies(cfr_agencies)
        
        logger.info(f"Found {len(active_cfr_agencies)} active agencies with CFR citations")
        return active_cfr_agencies
    
    def get_agency_statistics(self, agencies: List[Agency] = None) -> Dict[str, int]:
        """
        Get statistics about the loaded agencies.
        
        Args:
            agencies: List of agencies to analyze (uses loaded agencies if None)
            
        Returns:
            Dictionary with agency statistics
        """
        if agencies is None:
            agencies = self.agencies
        
        stats = {
            'total_agencies': len(agencies),
            'active_agencies': sum(1 for a in agencies if a.active),
            'inactive_agencies': sum(1 for a in agencies if not a.active),
            'agencies_with_cfr': sum(1 for a in agencies if a.cfr_citation),
            'agencies_without_cfr': sum(1 for a in agencies if not a.cfr_citation),
            'agencies_with_parent': sum(1 for a in agencies if a.parent_agency),
            'agencies_without_parent': sum(1 for a in agencies if not a.parent_agency),
        }
        
        return stats