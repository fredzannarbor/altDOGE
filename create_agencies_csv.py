#!/usr/bin/env python3
"""
Script to process Federal Register agencies JSON data and create a CSV file.
"""

import json
import csv
import re
from datetime import datetime

def extract_cfr_citation(description, agency_name):
    """Extract CFR citation from agency description."""
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
    desc_lower = description.lower()
    if any(keyword in desc_lower for keyword in ['banking', 'financial', 'currency']):
        return "12 CFR"  # Banking regulations
    elif any(keyword in desc_lower for keyword in ['securities', 'exchange', 'investment']):
        return "17 CFR"  # Securities regulations
    elif any(keyword in desc_lower for keyword in ['aviation', 'aircraft', 'airport']):
        return "14 CFR"  # Aviation regulations
    elif any(keyword in desc_lower for keyword in ['transportation', 'highway', 'motor']):
        return "49 CFR"  # Transportation regulations
    elif any(keyword in desc_lower for keyword in ['environment', 'pollution', 'clean']):
        return "40 CFR"  # Environmental regulations
    elif any(keyword in desc_lower for keyword in ['energy', 'power', 'electric']):
        return "10 CFR"  # Energy regulations
    elif any(keyword in desc_lower for keyword in ['labor', 'employment', 'worker']):
        return "29 CFR"  # Labor regulations
    elif any(keyword in desc_lower for keyword in ['health', 'medical', 'drug', 'food']):
        return "21 CFR"  # Health regulations
    elif any(keyword in desc_lower for keyword in ['agriculture', 'farm', 'crop']):
        return "7 CFR"   # Agriculture regulations
    elif any(keyword in desc_lower for keyword in ['education', 'school', 'student']):
        return "34 CFR"  # Education regulations
    
    return ""  # No CFR citation found

def determine_parent_agency(agency_data):
    """Determine the parent agency name."""
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

def is_agency_active(agency_data):
    """Determine if an agency is currently active."""
    description = agency_data.get('description') or ''
    description = description.lower()
    
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

def main():
    print("Processing Federal Register agencies data...")
    
    # Read the JSON data
    with open('agencies_raw.json', 'r', encoding='utf-8') as f:
        agencies = json.load(f)
    
    print(f"Found {len(agencies)} agencies")
    
    # Process each agency
    csv_data = []
    for agency_data in agencies:
        # Extract basic information
        name = agency_data.get('name', '')
        slug = agency_data.get('slug', '')
        description = agency_data.get('description', '')
        
        # Determine additional fields
        cfr_citation = extract_cfr_citation(description, name)
        parent_agency = determine_parent_agency(agency_data)
        active = is_agency_active(agency_data)
        
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
    
    # Generate filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"federal_register_agencies_{timestamp}.csv"
    
    # Save to CSV
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
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
    
    # Show statistics
    active_count = sum(1 for row in csv_data if row['active'] == '1')
    cfr_count = sum(1 for row in csv_data if row['cfr_citation'])
    
    print(f"\nCSV creation completed:")
    print(f"  Total agencies: {len(csv_data)}")
    print(f"  Active agencies: {active_count}")
    print(f"  Agencies with CFR citations: {cfr_count}")
    print(f"  File saved: {filename}")
    
    return filename

if __name__ == '__main__':
    main()