# CFR Document Analyzer - CSV Export Format Specification

## Overview

The CFR Document Analyzer exports analysis results in a restructured CSV format designed to improve data accessibility and usability. This document describes the new CSV format, changes from the previous version, and provides examples.

## New CSV Format Structure

### Column Headers

The restructured CSV format contains the following columns in order:

1. **Document Number** - Federal Register document number (e.g., "2024-12345")
2. **Title** - Document title
3. **Agency** - Full agency name (e.g., "National Credit Union Administration")
4. **Publication Date** - Document publication date (YYYY-MM-DD format)
5. **Content Length** - Document content length in characters
6. **Statutory References Count** - Number of statutory references found
7. **Statutory References** - Pipe-separated list of statutory references
8. **Reform Recommendations Count** - Number of reform recommendations
9. **Analysis Success** - Whether analysis completed successfully (Yes/No)
10. **Processing Time (s)** - Analysis processing time in seconds
11. **[Dynamic Justification Columns]** - Additional columns extracted from justification JSON data

### Dynamic Justification Columns

The justification field is parsed as JSON, and each key becomes a separate column. Common columns include:

- **category** - Regulation category (if present in justification)
- **statutory_authority** - Statutory authority information
- **legal_basis** - Legal basis for the regulation
- **analysis** - Analysis details
- **recommendation** - Specific recommendations
- **summary** - Summary information
- **conclusion** - Analysis conclusion

The exact columns will vary based on the structure of the justification data for each analysis session.

### Category Codes

The Category column uses the following standardized codes:

- **SR** - Statutorily Required: Required by specific statutory language
- **NSR** - Not Statutorily Required: Not required by statute but may be permissible
- **NRAN** - Not Required but Agency Needs: Not required by statute but needed for agency operations
- **UNKNOWN** - Analysis incomplete or category could not be determined

### Statutory References Format

Statutory references are formatted as a pipe-separated string to allow multiple references in a single cell while maintaining CSV compatibility:

- **Empty**: No statutory references found
- **Single**: `12 U.S.C. 1751`
- **Multiple**: `12 U.S.C. 1751|12 U.S.C. 1752(a)|15 U.S.C. 1601`

Special characters (including existing pipes) are cleaned from individual references to prevent parsing conflicts.

## Example CSV Output

```csv
Document Number,Title,Agency,Publication Date,Content Length,Statutory References Count,Statutory References,Reform Recommendations Count,Analysis Success,Processing Time (s),analysis,category,legal_basis,recommendation
2024-12345,Credit Union Capital Requirements,National Credit Union Administration,2024-01-15,2500,2,12 U.S.C. 1751|12 U.S.C. 1790d,1,Yes,3.20,Detailed analysis of capital requirements,SR,Federal Credit Union Act Section 216,Simplify reporting requirements
2024-67890,Member Business Lending Rules,National Credit Union Administration,2024-02-20,1800,0,,2,Yes,2.10,Review of business lending authority,NSR,12 U.S.C. 1757a,Modernize lending limits
2024-11111,Supervisory Committee Audits,National Credit Union Administration,2024-03-10,1200,1,12 U.S.C. 1761d,0,Yes,1.85,Audit requirement analysis,NRAN,Supervisory committee authority,Streamline audit procedures
2024-22222,Field of Membership Expansion,National Credit Union Administration,2024-04-05,3200,0,,1,No,0.50,,,Analysis incomplete,
```

## Changes from Previous Format

### Removed Columns

- **Category** - Removed as a fixed column; category information is now extracted from justification JSON if present
- **Justification Preview** - Removed to focus on structured data. Full justification text is available in JSON and HTML export formats.

### Added Columns

- **Statutory References** - New pipe-separated column containing the actual statutory references text, positioned after "Statutory References Count"
- **Dynamic Justification Columns** - Individual keys from the justification JSON are extracted as separate columns

### Modified Columns

- Column order has been optimized for logical grouping of related fields
- Justification data is now parsed as JSON and split into individual columns

### Unchanged Columns

All other columns maintain the same data types, formatting, and content as the previous version to ensure backward compatibility for existing analysis workflows.

## Migration Guide

### For Existing Users

If you have scripts or tools that process the old CSV format:

1. **Column Position Changes**: Update any column index references as the "Statutory References" column has been inserted
2. **Category Values**: Update category parsing to handle the new standardized codes (SR, NSR, NRAN, UNKNOWN)
3. **Justification Data**: If you need justification text, use the JSON or HTML export formats instead
4. **Statutory References**: Parse the new pipe-separated format if you need individual statutory references

### Example Migration Code

```python
# Old format parsing
def parse_old_csv(row):
    return {
        'document_number': row[0],
        'category': row[5],  # Full text like "Statutorily Required"
        'justification': row[10]  # Preview text
    }

# New format parsing
def parse_new_csv(row):
    return {
        'document_number': row[0],
        'category': row[5],  # Code like "SR"
        'statutory_refs': row[7].split('|') if row[7] else []  # Parse pipe-separated
    }

# Category code mapping
CATEGORY_MAPPING = {
    'SR': 'Statutorily Required',
    'NSR': 'Not Statutorily Required',
    'NRAN': 'Not Required but Agency Needs',
    'UNKNOWN': 'Analysis Incomplete'
}
```

## Spreadsheet Application Compatibility

The new CSV format has been tested with common spreadsheet applications:

### Microsoft Excel
- Pipe-separated statutory references display correctly
- Category codes sort and filter properly
- All data types are recognized correctly

### Google Sheets
- Full compatibility with all columns
- Pipe-separated data can be split using `SPLIT()` function
- Conditional formatting works with category codes

### LibreOffice Calc
- Complete compatibility
- Text-to-columns feature works with pipe separator
- All formatting preserved

## Usage Examples

### Filtering by Category

```bash
# Using command line tools
grep "^[^,]*,[^,]*,[^,]*,[^,]*,[^,]*,SR," analysis_results.csv

# Using Python pandas
import pandas as pd
df = pd.read_csv('analysis_results.csv')
statutorily_required = df[df['Category'] == 'SR']
```

### Parsing Statutory References

```python
import pandas as pd

df = pd.read_csv('analysis_results.csv')

# Split statutory references into lists
df['Statutory_Refs_List'] = df['Statutory References'].apply(
    lambda x: x.split('|') if x else []
)

# Count unique statutory references
all_refs = []
for refs in df['Statutory_Refs_List']:
    all_refs.extend(refs)
unique_refs = set(all_refs)
```

### Summary Statistics

```python
import pandas as pd

df = pd.read_csv('analysis_results.csv')

# Category distribution
category_counts = df['Category'].value_counts()

# Success rate
success_rate = (df['Analysis Success'] == 'Yes').mean() * 100

# Average processing time by category
avg_time_by_category = df.groupby('Category')['Processing Time (s)'].mean()
```

## Agency Synopsis Feature

In addition to the CSV restructuring, agency presentation reports now include an LLM-generated agency synopsis. This feature:

### Overview
- Generates a 100-word synopsis for each agency using AI analysis
- Includes statutory authority, history, role, and current issues
- Appears in agency presentation reports (Markdown format)

### Requirements
- Requires access to nimble-llm-caller for LLM integration
- API key configuration for the LLM service
- Network connectivity for synopsis generation

### Error Handling
- Graceful fallback when LLM service is unavailable
- Placeholder text when synopsis generation fails
- Does not affect CSV export functionality

### Example Synopsis
```
The National Credit Union Administration (NCUA) is an independent federal agency 
established in 1970 that regulates and supervises federal credit unions. Created 
under the Federal Credit Union Act, NCUA ensures the safety and soundness of the 
credit union system through examination, supervision, and deposit insurance. The 
agency operates the National Credit Union Share Insurance Fund, protecting member 
deposits up to $250,000. In today's Washington environment, NCUA faces challenges 
balancing regulatory oversight with credit union growth, addressing cybersecurity 
threats, and adapting regulations to technological innovations.
```

## Technical Implementation

### Data Extraction
- Category values are extracted from `analysis.category` field
- Handles both enum values and string representations
- Provides fallback to "UNKNOWN" for missing or invalid categories

### Reference Formatting
- Statutory references extracted from `analysis.statutory_references` array
- Pipe character (`|`) used as separator for CSV compatibility
- Existing pipes in reference text are replaced with spaces
- Empty references result in empty string

### Error Handling
- Missing data fields default to appropriate empty values
- Invalid data types are converted to string representations
- Processing continues even with malformed analysis results

## Support and Feedback

For questions about the new CSV format or migration assistance:

1. Review this specification document
2. Check the example outputs in the `results/` directory
3. Test with a small dataset before processing large batches
4. Report any compatibility issues or suggestions for improvement

## Version History

### Version 2.0 (Current)
- Restructured CSV format with pipe-separated statutory references
- Removed Justification Preview column
- Added standardized category codes
- Integrated agency synopsis generation
- Comprehensive test coverage

### Version 1.0 (Legacy)
- Original CSV format with justification preview
- Full text category descriptions
- Basic column structure