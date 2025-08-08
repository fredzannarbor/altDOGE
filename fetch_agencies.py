#!/usr/bin/env python3
"""
Standalone script to fetch Federal Register agencies and create a CSV file.

This script can be run directly to download all agencies from the Federal Register API
and create a properly formatted CSV file for use with the document counter.
"""

import sys
import os
import logging
from datetime import datetime

# Add the current directory to Python path so we can import our modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from cfr_agency_counter.agency_fetcher import AgencyFetcher
from cfr_agency_counter.api_client import FederalRegisterClient

def main():
    """Main function to fetch agencies and create CSV."""
    print("Fetching all agencies from Federal Register API...")
    
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    try:
        # Create API client with rate limiting
        api_client = FederalRegisterClient(rate_limit=0.5)
        
        # Create fetcher and generate CSV
        fetcher = AgencyFetcher(api_client)
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"federal_register_agencies_{timestamp}.csv"
        
        filepath = fetcher.create_agencies_csv(filename)
        
        print(f"\nSuccess! Agencies CSV created: {filepath}")
        print("\nYou can now use this file with the document counter:")
        print(f"  python3 -m cfr_agency_counter.main {filepath}")
        
        return 0
        
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        return 130
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

if __name__ == '__main__':
    sys.exit(main())