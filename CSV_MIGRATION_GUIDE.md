# CSV Format Migration Guide

## Overview

This guide helps users migrate from the old CSV export format to the new restructured format introduced in CFR Document Analyzer v2.0.

## Quick Reference

### Column Changes Summary

| Change Type | Old Format | New Format | Notes |
|-------------|------------|------------|-------|
| **Removed** | Justification Preview (column 11) | *(removed)* | Use JSON/HTML exports for full text |
| **Added** | *(none)* | Statutory References (column 8) | Pipe-separated list |
| **Modified** | Category (full text) | Category (codes) | SR, NSR, NRAN, UNKNOWN |
| **Reordered** | Various positions | Logical grouping | See column mapping below |

### Column Position Mapping

| Column Name | Old Position | New Position | Change |
|-------------|--------------|--------------|--------|
| Document Number | 1 | 1 | No change |
| Title | 2 | 2 | No change |
| Agency | 3 | 3 | No change |
| Publication Date | 4 | 4 | No change |
| Content Length | 5 | 5 | No change |
| Category | 6 | 6 | **Format changed** |
| Statutory References Count | 7 | 7 | No change |
| **Statutory References** | *(new)* | **8** | **New column** |
| Reform Recommendations Count | 8 | 9 | Moved right |
| Analysis Success | 9 | 10 | Moved right |
| Processing Time (s) | 10 | 11 | Moved right |
| **Justification Preview** | **11** | *(removed)* | **Removed** |

## Code Migration Examples

### Python with Pandas

#### Old Format Code
```python
import pandas as pd

# Old format parsing
def process_old_format(csv_file):
    df = pd.read_csv(csv_file)
    
    # Access columns by position (fragile)
    document_numbers = df.iloc[:, 0]
    categories = df.iloc[:, 5]  # Full text categories
    justifications = df.iloc[:, 10]  # Preview text
    
    # Filter by category (full text matching)
    statutorily_required = df[df.iloc[:, 5] == 'Statutorily Required']
    
    return df
```

#### New Format Code
```python
import pandas as pd

# New format parsing
def process_new_format(csv_file):
    df = pd.read_csv(csv_file)
    
    # Access columns by name (robust)
    document_numbers = df['Document Number']
    categories = df['Category']  # Code format
    statutory_refs = df['Statutory References']  # Pipe-separated
    
    # Filter by category (code matching)
    statutorily_required = df[df['Category'] == 'SR']
    
    # Parse statutory references
    df['Statutory_Refs_List'] = df['Statutory References'].apply(
        lambda x: x.split('|') if x else []
    )
    
    return df

# Category code mapping for display
CATEGORY_NAMES = {
    'SR': 'Statutorily Required',
    'NSR': 'Not Statutorily Required', 
    'NRAN': 'Not Required but Agency Needs',
    'UNKNOWN': 'Analysis Incomplete'
}

def add_category_names(df):
    df['Category_Name'] = df['Category'].map(CATEGORY_NAMES)
    return df
```

### Python with CSV Module

#### Old Format Code
```python
import csv

def read_old_format(csv_file):
    results = []
    with open(csv_file, 'r') as f:
        reader = csv.reader(f)
        headers = next(reader)  # Skip headers
        
        for row in reader:
            result = {
                'document_number': row[0],
                'category': row[5],  # Full text
                'justification': row[10],  # Preview
                'success': row[8] == 'Yes'
            }
            results.append(result)
    
    return results
```

#### New Format Code
```python
import csv

def read_new_format(csv_file):
    results = []
    with open(csv_file, 'r') as f:
        reader = csv.DictReader(f)  # Use DictReader for robustness
        
        for row in reader:
            # Parse statutory references
            statutory_refs = []
            if row['Statutory References']:
                statutory_refs = row['Statutory References'].split('|')
            
            result = {
                'document_number': row['Document Number'],
                'category': row['Category'],  # Code format
                'statutory_references': statutory_refs,  # Parsed list
                'success': row['Analysis Success'] == 'Yes'
            }
            results.append(result)
    
    return results
```

### Excel/VBA Migration

#### Old Format VBA
```vb
' Old format - fragile column references
Sub ProcessOldFormat()
    Dim ws As Worksheet
    Set ws = ActiveSheet
    
    ' Column references by position
    Dim categoryCol As Integer: categoryCol = 6
    Dim justificationCol As Integer: justificationCol = 11
    
    ' Filter for "Statutorily Required"
    ws.Range("A1").AutoFilter Field:=categoryCol, Criteria1:="Statutorily Required"
End Sub
```

#### New Format VBA
```vb
' New format - robust column references
Sub ProcessNewFormat()
    Dim ws As Worksheet
    Set ws = ActiveSheet
    
    ' Find column positions by header name
    Dim categoryCol As Integer
    Dim statutoryRefsCol As Integer
    
    For i = 1 To ws.Cells(1, ws.Columns.Count).End(xlToLeft).Column
        If ws.Cells(1, i).Value = "Category" Then categoryCol = i
        If ws.Cells(1, i).Value = "Statutory References" Then statutoryRefsCol = i
    Next i
    
    ' Filter for "SR" (Statutorily Required)
    ws.Range("A1").AutoFilter Field:=categoryCol, Criteria1:="SR"
    
    ' Split statutory references in adjacent column
    For Each cell In ws.Range(ws.Cells(2, statutoryRefsCol), ws.Cells(ws.Rows.Count, statutoryRefsCol).End(xlUp))
        If cell.Value <> "" Then
            cell.Offset(0, 1).Value = Replace(cell.Value, "|", ", ")
        End If
    Next cell
End Sub
```

## Common Migration Tasks

### 1. Update Category Filtering

**Old approach:**
```python
# Full text matching
sr_docs = df[df['Category'] == 'Statutorily Required']
nsr_docs = df[df['Category'] == 'Not Statutorily Required']
```

**New approach:**
```python
# Code matching (more efficient)
sr_docs = df[df['Category'] == 'SR']
nsr_docs = df[df['Category'] == 'NSR']
nran_docs = df[df['Category'] == 'NRAN']
unknown_docs = df[df['Category'] == 'UNKNOWN']
```

### 2. Handle Justification Text

**Old approach:**
```python
# Preview text from CSV
justification_preview = df['Justification Preview']
```

**New approach:**
```python
# Use JSON export for full justification text
import json

with open('analysis_results.json', 'r') as f:
    data = json.load(f)
    
for result in data['results']:
    full_justification = result['analysis']['justification']
```

### 3. Parse Statutory References

**New capability:**
```python
# Extract individual statutory references
def parse_statutory_refs(refs_string):
    if not refs_string:
        return []
    return [ref.strip() for ref in refs_string.split('|')]

df['Statutory_Refs_List'] = df['Statutory References'].apply(parse_statutory_refs)

# Find all unique statutory references
all_refs = set()
for refs_list in df['Statutory_Refs_List']:
    all_refs.update(refs_list)

print(f"Found {len(all_refs)} unique statutory references")
```

### 4. Update Column Index References

**Old approach (fragile):**
```python
# Hard-coded column positions
document_col = 0
category_col = 5
success_col = 8
time_col = 9
```

**New approach (robust):**
```python
# Use column names
df = pd.read_csv('results.csv')
documents = df['Document Number']
categories = df['Category']
success = df['Analysis Success']
processing_time = df['Processing Time (s)']
```

## Testing Your Migration

### 1. Validate Column Structure

```python
def validate_csv_format(csv_file):
    """Validate that CSV has expected new format structure."""
    expected_columns = [
        'Document Number', 'Title', 'Agency', 'Publication Date', 
        'Content Length', 'Category', 'Statutory References Count',
        'Statutory References', 'Reform Recommendations Count',
        'Analysis Success', 'Processing Time (s)'
    ]
    
    df = pd.read_csv(csv_file)
    
    if list(df.columns) != expected_columns:
        print("❌ Column structure mismatch")
        print(f"Expected: {expected_columns}")
        print(f"Found: {list(df.columns)}")
        return False
    
    print("✅ Column structure is correct")
    return True
```

### 2. Verify Category Codes

```python
def validate_categories(csv_file):
    """Validate category codes are in expected format."""
    valid_categories = {'SR', 'NSR', 'NRAN', 'UNKNOWN'}
    
    df = pd.read_csv(csv_file)
    found_categories = set(df['Category'].unique())
    
    invalid_categories = found_categories - valid_categories
    if invalid_categories:
        print(f"❌ Invalid categories found: {invalid_categories}")
        return False
    
    print("✅ All categories are valid")
    return True
```

### 3. Test Statutory References Parsing

```python
def test_statutory_refs_parsing(csv_file):
    """Test parsing of pipe-separated statutory references."""
    df = pd.read_csv(csv_file)
    
    for idx, refs_str in enumerate(df['Statutory References']):
        if refs_str:  # Skip empty references
            refs_list = refs_str.split('|')
            count = df.loc[idx, 'Statutory References Count']
            
            if len(refs_list) != count:
                print(f"❌ Mismatch at row {idx}: count={count}, actual={len(refs_list)}")
                return False
    
    print("✅ Statutory references parsing is correct")
    return True
```

## Rollback Plan

If you need to temporarily revert to the old format while migrating:

### Option 1: Use JSON Export
```python
# Convert JSON export to old-style CSV
import json
import csv

def json_to_old_csv(json_file, csv_file):
    with open(json_file, 'r') as f:
        data = json.load(f)
    
    with open(csv_file, 'w', newline='') as f:
        writer = csv.writer(f)
        
        # Old format headers
        headers = [
            'Document Number', 'Title', 'Agency', 'Publication Date',
            'Content Length', 'Category', 'Statutory References Count',
            'Reform Recommendations Count', 'Analysis Success',
            'Processing Time (s)', 'Justification Preview'
        ]
        writer.writerow(headers)
        
        for result in data['results']:
            analysis = result['analysis']
            
            # Convert category code back to full text
            category_map = {
                'SR': 'Statutorily Required',
                'NSR': 'Not Statutorily Required',
                'NRAN': 'Not Required but Agency Needs',
                'UNKNOWN': 'UNKNOWN'
            }
            
            category = category_map.get(analysis.get('category', 'UNKNOWN'), 'UNKNOWN')
            
            # Truncate justification for preview
            justification = analysis.get('justification', '')
            preview = justification[:200] + '...' if len(justification) > 200 else justification
            
            row = [
                result['document_number'],
                result['title'],
                result['agency'],  # Assuming this is extracted
                result.get('publication_date', ''),
                result.get('content_length', 0),
                category,
                len(analysis.get('statutory_references', [])),
                len(analysis.get('reform_recommendations', [])),
                'Yes' if analysis.get('success') else 'No',
                f"{analysis.get('processing_time', 0):.2f}",
                preview
            ]
            writer.writerow(row)
```

### Option 2: Temporary Format Flag
If you control the export code, you could add a temporary compatibility flag:

```python
# In your export configuration
export_manager = ExportManager()
results = export_manager.export_session_results(
    results, 
    session_id, 
    formats=['csv_legacy']  # Temporary legacy format
)
```

## Support and Troubleshooting

### Common Issues

1. **"Column not found" errors**
   - Update hard-coded column indices to use column names
   - Verify CSV file has correct headers

2. **Category filtering returns no results**
   - Update category values from full text to codes (SR, NSR, NRAN, UNKNOWN)

3. **Statutory references appear as single string**
   - Parse pipe-separated values: `refs.split('|')`

4. **Missing justification text**
   - Use JSON or HTML export formats for full justification text

### Getting Help

1. Review the [CSV Format Specification](CSV_FORMAT_SPECIFICATION.md)
2. Check example files in the `examples/` directory
3. Test with small datasets before processing large files
4. Validate your migrated code with the test functions above

### Migration Checklist

- [ ] Update column position references to use column names
- [ ] Change category filtering from full text to codes
- [ ] Add statutory references parsing for pipe-separated values
- [ ] Switch to JSON/HTML exports for justification text
- [ ] Test with sample data before production use
- [ ] Update documentation and user guides
- [ ] Train users on new format and features