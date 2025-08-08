# Implementation Plan

- [x] 1. Update CSV export column structure and data extraction
  - Modify the `_export_csv` method in `ExportManager` to use new column headers
  - Implement data extraction logic to get category and statutory references from analysis objects
  - Remove Justification Preview column and related data processing
  - _Requirements: 1.1, 2.1, 3.1_

- [x] 2. Implement statutory references formatting
  - Create helper method to format statutory references as pipe-separated string
  - Handle empty, single, and multiple statutory references cases
  - Add proper escaping for CSV format compatibility
  - _Requirements: 2.2, 2.3, 2.4_

- [x] 3. Add category extraction and formatting
  - Implement category extraction from analysis.category field
  - Handle RegulationCategory enum values and string representations
  - Provide fallback to "UNKNOWN" for missing or invalid categories
  - _Requirements: 1.2, 1.3, 1.4, 1.5_

- [x] 4. Create agency synopsis generation functionality
  - Add method to generate LLM-based agency synopsis using nimble-llm-caller
  - Implement 100-word synopsis prompt covering statutory authority, history, role, and current issues
  - Add error handling and fallback for failed LLM calls
  - _Requirements: 7.1, 7.2, 7.3, 7.4_

- [x] 5. Integrate agency synopsis into presentation reports
  - Modify `create_agency_presentation_summary` to include LLM-generated synopsis
  - Add synopsis to report header section with proper formatting
  - Handle synopsis generation failures gracefully with placeholder text
  - _Requirements: 7.5, 7.3, 7.4_

- [x] 6. Update all CSV export functions for consistency
  - Ensure batch export functions use new CSV structure
  - Update any other methods that generate CSV output
  - Maintain consistency across all export pathways
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_

- [x] 7. Add comprehensive unit tests for CSV restructuring
  - Test new CSV column structure and header generation
  - Test category extraction from various analysis result formats
  - Test statutory references formatting with different input scenarios
  - Test error handling for missing or invalid data
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

- [x] 8. Add integration tests for agency synopsis feature
  - Test complete agency presentation generation with LLM synopsis
  - Test LLM call error handling and fallback behavior
  - Test synopsis integration into report formatting
  - Test async processing and timeout handling
  - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5_

- [x] 9. Update documentation and examples
  - Update README with new CSV format specification
  - Add examples of restructured CSV output
  - Document agency synopsis feature and requirements
  - Provide migration guidance for users of old format
  - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_

- [x] 10. Validate CSV format compatibility
  - Test CSV files with common spreadsheet applications (Excel, Google Sheets)
  - Verify pipe-separated statutory references are properly handled
  - Test Unicode and special character handling in CSV output
  - Ensure proper escaping of CSV special characters
  - _Requirements: 5.5, 2.5, 4.5_