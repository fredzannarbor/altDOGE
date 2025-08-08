#!/usr/bin/env python3
"""
Agency Fetcher for downloading and formatting Federal Register agencies.

This module fetches all agencies from the Federal Register API and creates
a properly formatted CSV file that can be used with the document counter.
"""

import csv
import logging
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

from .api_client import FederalRegisterClient, FederalRegisterAPIError
from .models import Agency


logger = logging.getLogger(__name__)


class AgencyFetcher:
    """Fetches agencies from Federal Register API and creates formatted CSV files."""
    
    def __init__(self, api_client: Optional[FederalRegisterClient] = None):
        """
        Initialize the agency fetcher.
        
        Args:
            api_client: Optional API client instance. If None, creates a new one.
        """
        self.api_client = api_client or FederalRegisterClient(rate_limit=0.5)
        logger.info("Agency fetcher initialized")
    
    def fetch_all_agencies(self) -> List[Dict[str, Any]]:
        """
        Fetch all agencies from the Federal Register API.
        
        Returns:
            List of agency dictionaries from the API
            
        Raises:
            FederalRegisterAPIError: If the API request fails
        """
        logger.info("Fetching all agencies from Federal Register API")
        
        try:
            agencies = self.api_client.get_all_agencies()
            logger.info(f"Successfully fetched {len(agencies)} agencies")
            return agencies
            
        except Exception as e:
            logger.error(f"Failed to fetch agencies: {e}")
            raise FederalRegisterAPIError(f"Failed to fetch agencies: {e}")
    
    def extract_cfr_citation(self, description: str, agency_name: str) -> str:
        """
        Extract CFR citation from agency description.
        
        Args:
            description: Agency description text
            agency_name: Agency name for context
            
        Returns:
            CFR citation string or empty string if not found
        """
        if not description:
            return ""
        
        # Common CFR citation patterns
        patterns = [
            r'(\d+)\s+CFR\s+(\d+(?:\.\d+)?(?:-\d+(?:\.\d+)?)?)',  # "12 CFR 100-199"
            r'CFR\s+(\d+)\s+(\d+(?:\.\d+)?(?:-\d+(?:\.\d+)?)?)',   # "CFR 12 100-199"
            r'(\d+)\s+C\.F\.R\.\s+(\d+(?:\.\d+)?(?:-\d+(?:\.\d+)?)?)',  # "12 C.F.R. 100-199"
            r'Title\s+(\d+)\s+CFR',  # "Title 12 CFR"
            r'Title\s+(\d+)\s+Code\s+of\s+Federal\s+Regulations'  # "Title 12 Code of Federal Regulations"
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, description, re.IGNORECASE)
            if matches:
                if len(matches[0]) == 2:  # Title and section
                    title, section = matches[0]
                    return f"{title} CFR {section}"
                else:  # Just title
                    title = matches[0]
                    return f"{title} CFR"
        
        # Try to infer from common agency types
        if any(keyword in description.lower() for keyword in ['banking', 'financial', 'currency']):
            return "12 CFR"  # Banking regulations
        elif any(keyword in description.lower() for keyword in ['securities', 'exchange', 'investment']):
            return "17 CFR"  # Securities regulations
        elif any(keyword in description.lower() for keyword in ['aviation', 'aircraft', 'airport']):
            return "14 CFR"  # Aviation regulations
        elif any(keyword in description.lower() for keyword in ['transportation', 'highway', 'motor']):
            return "49 CFR"  # Transportation regulations
        elif any(keyword in description.lower() for keyword in ['environment', 'pollution', 'clean']):
            return "40 CFR"  # Environmental regulations
        elif any(keyword in description.lower() for keyword in ['energy', 'power', 'electric']):
            return "10 CFR"  # Energy regulations
        elif any(keyword in description.lower() for keyword in ['labor', 'employment', 'worker']):
            return "29 CFR"  # Labor regulations
        elif any(keyword in description.lower() for keyword in ['health', 'medical', 'drug', 'food']):
            return "21 CFR"  # Health regulations
        elif any(keyword in description.lower() for keyword in ['agriculture', 'farm', 'crop']):
            return "7 CFR"   # Agriculture regulations
        elif any(keyword in description.lower() for keyword in ['education', 'school', 'student']):
            return "34 CFR"  # Education regulations
        
        return ""  # No CFR citation found
    
    def determine_parent_agency(self, agency_data: Dict[str, Any]) -> str:
        """
        Determine the parent agency name.
        
        Args:
            agency_data: Agency data from API
            
        Returns:
            Parent agency name or the agency name itself if no parent
        """
        # If there's a parent_id, we'd need to look it up, but for now use the agency name
        # In a full implementation, you might want to build a parent-child mapping
        
        name = agency_data.get('name', '')
        
        # Common department patterns
        if 'Department' in name:
            return name
        elif any(dept in name for dept in ['Treasury', 'Commerce', 'Defense', 'Energy', 'Health']):
            # Extract department name
            for dept in ['Treasury', 'Commerce', 'Defense', 'Energy', 'Health and Human Services']:
                if dept.split()[0].lower() in name.lower():
                    return f"{dept} Department"
        
        # Default to the agency name itself
        return name
    
    def is_agency_active(self, agency_data: Dict[str, Any]) -> bool:
        """
        Determine if an agency is currently active.
        
        Args:
            agency_data: Agency data from API
            
        Returns:
            True if agency appears to be active
        """
        description = agency_data.get('description', '').lower()
        
        # Check for indicators of inactive agencies
        inactive_indicators = [
            'abolished', 'terminated', 'dissolved', 'ceased', 'discontinued',
            'transferred to', 'merged into', 'replaced by', 'succeeded by',
            'no longer', 'former', 'was a', 'was an'
        ]
        
        for indicator in inactive_indicators:
            if indicator in description:
                return False
        
        # If we can't determine, assume active
        return True
    
    def convert_to_csv_format(self, agencies: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        """
        Convert API agency data to CSV format.
        
        Args:
            agencies: List of agency dictionaries from API
            
        Returns:
            List of dictionaries formatted for CSV output
        """
        logger.info(f"Converting {len(agencies)} agencies to CSV format")
        
        csv_data = []
        
        for agency_data in agencies:
            # Extract basic information
            name = agency_data.get('name', '')
            slug = agency_data.get('slug', '')
            description = agency_data.get('description', '')
            
            # Determine additional fields
            cfr_citation = self.extract_cfr_citation(description, name)
            parent_agency = self.determine_parent_agency(agency_data)
            active = self.is_agency_active(agency_data)
            
            # Clean description (remove newlines, limit length)
            clean_description = ' '.join(description.split())[:500] if description else ''
            
            csv_row = {
                'active': '1' if active else '0',
                'cfr_citation': cfr_citation,
                'parent_agency_name': parent_agency,
                'agency_name': name,
                'description': clean_description,
                'slug': slug,  # Additional field for reference
                'api_id': str(agency_data.get('id', '')),  # Additional field for reference
            }
            
            csv_data.append(csv_row)
        
        logger.info(f"Converted {len(csv_data)} agencies to CSV format")
        return csv_data
    
    def save_agencies_csv(self, csv_data: List[Dict[str, str]], filename: str) -> str:
        """
        Save agency data to CSV file.
        
        Args:
            csv_data: List of dictionaries with agency data
            filename: Output filename
            
        Returns:
            Path to the saved CSV file
            
        Raises:
            IOError: If file cannot be written
        """
        filepath = Path(filename)
        
        logger.info(f"Saving {len(csv_data)} agencies to {filepath}")
        
        try:
            with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
                # Define fieldnames in the order expected by the document counter
                fieldnames = [
                    'active',
                    'cfr_citation', 
                    'parent_agency_name',
                    'agency_name',
                    'description',
                    'slug',  # Additional field
                    'api_id'  # Additional field
                ]
                
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames, quoting=csv.QUOTE_MINIMAL)
                writer.writeheader()
                writer.writerows(csv_data)
            
            logger.info(f"Successfully saved agencies to {filepath}")
            return str(filepath)
            
        except IOError as e:
            logger.error(f"Failed to save CSV file: {e}")
            raise IOError(f"Failed to save CSV file {filepath}: {e}")
    
    def create_agencies_csv(self, filename: Optional[str] = None) -> str:
        """
        Fetch all agencies and create a formatted CSV file.
        
        Args:
            filename: Optional output filename. If None, auto-generates with timestamp.
            
        Returns:
            Path to the created CSV file
            
        Raises:
            FederalRegisterAPIError: If API request fails
            IOError: If file cannot be written
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"federal_register_agencies_{timestamp}.csv"
        
        logger.info(f"Creating agencies CSV file: {filename}")
        
        # Fetch agencies from API
        agencies = self.fetch_all_agencies()
        
        # Convert to CSV format
        csv_data = self.convert_to_csv_format(agencies)
        
        # Save to file
        filepath = self.save_agencies_csv(csv_data, filename)
        
        # Log statistics
        active_count = sum(1 for row in csv_data if row['active'] == '1')
        cfr_count = sum(1 for row in csv_data if row['cfr_citation'])
        
        logger.info(f"CSV creation completed:")
        logger.info(f"  Total agencies: {len(csv_data)}")
        logger.info(f"  Active agencies: {active_count}")
        logger.info(f"  Agencies with CFR citations: {cfr_count}")
        logger.info(f"  File saved: {filepath}")
        
        return filepath
    
    def get_agency_statistics(self, csv_data: List[Dict[str, str]]) -> Dict[str, int]:
        """
        Get statistics about the agency data.
        
        Args:
            csv_data: List of agency dictionaries
            
        Returns:
            Dictionary with statistics
        """
        stats = {
            'total_agencies': len(csv_data),
            'active_agencies': sum(1 for row in csv_data if row['active'] == '1'),
            'inactive_agencies': sum(1 for row in csv_data if row['active'] == '0'),
            'agencies_with_cfr': sum(1 for row in csv_data if row['cfr_citation']),
            'agencies_without_cfr': sum(1 for row in csv_data if not row['cfr_citation']),
        }
        
        # Count by CFR title
        cfr_titles = {}
        for row in csv_data:
            if row['cfr_citation']:
                title = row['cfr_citation'].split()[0] if row['cfr_citation'] else 'Unknown'
                cfr_titles[title] = cfr_titles.get(title, 0) + 1
        
        stats['cfr_title_distribution'] = cfr_titles
        
        return stats


def main():
    """Command-line interface for the agency fetcher."""
    import argparse
    import sys
    
    parser = argparse.ArgumentParser(
        description="Fetch Federal Register agencies and create CSV file"
    )
    parser.add_argument(
        '--output', '-o',
        help='Output CSV filename (default: auto-generated with timestamp)'
    )
    parser.add_argument(
        '--rate-limit',
        type=float,
        default=0.5,
        help='API rate limit in requests per second (default: 0.5)'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    # Set up logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    try:
        # Create API client with specified rate limit
        api_client = FederalRegisterClient(rate_limit=args.rate_limit)
        
        # Create fetcher and generate CSV
        fetcher = AgencyFetcher(api_client)
        filepath = fetcher.create_agencies_csv(args.output)
        
        print(f"\nSuccess! Agencies CSV created: {filepath}")
        print("\nYou can now use this file with the document counter:")
        print(f"  python -m cfr_agency_counter.main {filepath}")
        
        return 0
        
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        return 130
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())