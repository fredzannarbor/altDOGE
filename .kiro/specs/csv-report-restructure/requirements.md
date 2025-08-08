# Requirements Document

## Introduction

This feature restructures the CSV export format for the CFR Document Analyzer to improve data accessibility and usability. Based on successful LLM analysis results, the current CSV format needs to be reorganized to extract key information from the JSON justification preview into dedicated columns, making the data more structured and easier to analyze in spreadsheet applications.

## Requirements

### Requirement 1

**User Story:** As a data analyst, I want the document category extracted from the JSON justification into a dedicated Category column, so that I can easily filter and sort documents by their regulatory classification without parsing JSON.

#### Acceptance Criteria

1. WHEN exporting CSV results THEN the system SHALL create a dedicated "Category" column positioned after "Content Length"
2. WHEN processing analysis results THEN the system SHALL extract the category value from the analysis.category field
3. WHEN category data is available THEN the system SHALL populate the Category column with values like "SR", "NSR", "NRAN", or "UNKNOWN"
4. WHEN category data is missing THEN the system SHALL populate the Category column with "UNKNOWN"
5. WHEN CSV is generated THEN the Category column SHALL contain only the category code without additional JSON formatting

### Requirement 2

**User Story:** As a regulatory researcher, I want statutory references extracted from the JSON into a dedicated column, so that I can easily review and analyze the legal foundations of each regulation without parsing complex JSON structures.

#### Acceptance Criteria

1. WHEN exporting CSV results THEN the system SHALL create a dedicated "Statutory References" column positioned after "Statutory References Count"
2. WHEN processing analysis results THEN the system SHALL extract statutory references from the analysis.statutory_references field
3. WHEN multiple statutory references exist THEN the system SHALL format them as a pipe-separated list (e.g., "20 U.S.C. 9252(a)|20 U.S.C. 9252(c)(1)(A)")
4. WHEN no statutory references exist THEN the system SHALL leave the Statutory References column empty
5. WHEN statutory references are truncated in JSON THEN the system SHALL include the full available text without truncation indicators

### Requirement 3

**User Story:** As a user working with CSV data, I want the Justification Preview column removed, so that the CSV file is cleaner and focuses on structured data rather than preview text that's better suited for other report formats.

#### Acceptance Criteria

1. WHEN exporting CSV results THEN the system SHALL NOT include a "Justification Preview" column
2. WHEN generating CSV headers THEN the system SHALL exclude "Justification Preview" from the header row
3. WHEN writing CSV data rows THEN the system SHALL NOT include justification preview data
4. WHEN users need full justification text THEN the system SHALL direct them to JSON or HTML export formats
5. WHEN CSV export is complete THEN the file SHALL contain only structured data columns without preview text

### Requirement 4

**User Story:** As a system administrator, I want these CSV format changes applied consistently across all export functions, so that users get the same improved format regardless of how they generate reports.

#### Acceptance Criteria

1. WHEN any CSV export function is called THEN the system SHALL use the new column structure
2. WHEN batch exports are generated THEN the system SHALL apply the new format to all CSV files
3. WHEN agency presentation summaries include CSV data THEN the system SHALL use the restructured format
4. WHEN session results are exported THEN the system SHALL generate CSV files with the new column arrangement
5. WHEN export formats are mixed THEN the system SHALL maintain consistency between CSV structure and other format content

### Requirement 5

**User Story:** As a data analyst, I want the new CSV format to maintain backward compatibility for essential data fields, so that existing analysis workflows continue to work with the restructured export.

#### Acceptance Criteria

1. WHEN exporting with the new format THEN the system SHALL preserve all existing data fields except Justification Preview
2. WHEN column order changes THEN the system SHALL maintain logical grouping of related fields
3. WHEN field names are used THEN the system SHALL keep existing field names for unchanged columns
4. WHEN data types are processed THEN the system SHALL maintain the same data types and formatting for existing fields
5. WHEN CSV files are imported into analysis tools THEN the system SHALL ensure compatibility with common spreadsheet applications

### Requirement 6

**User Story:** As a user, I want clear documentation of the new CSV format, so that I understand what data is available in each column and how to interpret the restructured export.

#### Acceptance Criteria

1. WHEN CSV format is updated THEN the system SHALL update all relevant documentation
2. WHEN users request format information THEN the system SHALL provide clear column descriptions
3. WHEN examples are needed THEN the system SHALL include sample CSV output in documentation
4. WHEN migration is required THEN the system SHALL provide guidance for users transitioning from the old format
5. WHEN format questions arise THEN the system SHALL include format specification in help text and README files

### Requirement 7

**User Story:** As a policy analyst, I want agency reports to include a concise agency overview generated by LLM analysis, so that I can quickly understand the agency's role and current context when reviewing regulatory analysis results.

#### Acceptance Criteria

1. WHEN generating agency presentation summaries THEN the system SHALL call nimble-llm-caller to generate a 100-word agency synopsis
2. WHEN creating the agency synopsis THEN the system SHALL include the agency's statutory authority, history, informal description of its role, and key issues in today's Washington
3. WHEN the LLM call succeeds THEN the system SHALL include the synopsis in the agency report header section
4. WHEN the LLM call fails THEN the system SHALL include a placeholder indicating the synopsis could not be generated
5. WHEN the synopsis is generated THEN the system SHALL format it as a readable paragraph in the agency presentation document