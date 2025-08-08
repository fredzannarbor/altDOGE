#!/usr/bin/env python3
"""
Debug script to examine Federal Register search page structure.
"""

import requests
from bs4 import BeautifulSoup
import re

def debug_search_page(agency_slug):
    """Debug the search page for a specific agency."""
    
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    })
    
    search_url = "https://www.federalregister.gov/documents/search"
    params = {
        'conditions[agencies][]': agency_slug,
        'order': 'newest'
    }
    
    print(f"Fetching: {search_url}")
    print(f"Params: {params}")
    
    try:
        response = session.get(search_url, params=params, timeout=30, allow_redirects=True)
        print(f"Status: {response.status_code}")
        print(f"Final URL: {response.url}")
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Look for count-related text
            full_text = soup.get_text()
            
            print("\n=== SEARCHING FOR COUNT PATTERNS ===")
            patterns = [
                r'showing\s+\d+\s*-\s*\d+\s+of\s+([\d,]+)\s+results?',
                r'([\d,]+)\s+documents?\s+found',
                r'found\s+([\d,]+)\s+documents?',
                r'([\d,]+)\s+total\s+results?',
                r'results?\s*:\s*([\d,]+)',
                r'([\d,]+)\s+matches?',
                r'([\d,]+)\s+documents?\s+match\s+your\s+search',
            ]
            
            for pattern in patterns:
                matches = re.findall(pattern, full_text, re.IGNORECASE)
                if matches:
                    print(f"Pattern '{pattern}' found: {matches}")
            
            # Look for specific elements
            print("\n=== SEARCHING FOR SPECIFIC ELEMENTS ===")
            elements_to_check = [
                ('div', 'search-count'),
                ('div', 'results-count'),
                ('div', 'search-summary'),
                ('div', 'pagination-summary'),
                ('span', 'search-count'),
                ('p', 'search-summary'),
                ('div', 'pagination'),
                ('nav', 'pagination'),
            ]
            
            for tag, class_name in elements_to_check:
                element = soup.find(tag, class_=class_name)
                if element:
                    print(f"Found {tag}.{class_name}: {element.get_text().strip()}")
            
            # Look for any text containing numbers
            print("\n=== ALL TEXT WITH NUMBERS ===")
            lines_with_numbers = []
            for line in full_text.split('\n'):
                if re.search(r'\d+', line.strip()) and len(line.strip()) < 200:
                    clean_line = ' '.join(line.strip().split())
                    if clean_line and 'javascript' not in clean_line.lower():
                        lines_with_numbers.append(clean_line)
            
            for line in lines_with_numbers[:20]:  # Show first 20 lines
                print(f"  {line}")
            
            # Count visible result items
            result_items = soup.find_all(['div', 'li'], class_=re.compile(r'document|result|item'))
            print(f"\n=== VISIBLE RESULT ITEMS ===")
            print(f"Found {len(result_items)} result items")
            
            # Show some result item classes
            for item in result_items[:5]:
                print(f"  Item class: {item.get('class', [])}")
        
        else:
            print(f"Error: HTTP {response.status_code}")
            print(response.text[:500])
    
    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    debug_search_page('administrative-conference-of-the-united-states')