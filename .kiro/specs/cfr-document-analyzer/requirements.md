# Requirements Document

## Introduction

This feature extends the existing CFR agency document counter to create a comprehensive document analysis system. The system will retrieve CFR documents by agency, run configurable LLM prompts against the document content, and provide aggregated analysis and statistics. This enables researchers and analysts to perform systematic content analysis across regulatory documents using AI-powered insights.

## Requirements

### Requirement 1

**User Story:** As a regulatory researcher, I want to retrieve CFR documents by agency and analyze them with custom prompts, so that I can extract specific insights and patterns from regulatory text at scale.

#### Acceptance Criteria

1. WHEN a user specifies an agency THEN the system SHALL retrieve all available CFR documents for that agency
2. WHEN documents are retrieved THEN the system SHALL extract the full text content from each document
3. WHEN document content is available THEN the system SHALL apply user-defined LLM prompts to analyze the content
4. IF a document cannot be retrieved or processed THEN the system SHALL log the error and continue with remaining documents
5. WHEN analysis is complete THEN the system SHALL provide aggregated results and statistics

### Requirement 2

**User Story:** As an analyst, I want to configure multiple analysis prompts for different aspects of regulatory content, so that I can extract various types of insights from the same document set.

#### Acceptance Criteria

1. WHEN configuring analysis THEN the system SHALL accept multiple custom prompts from the user
2. WHEN prompts are provided THEN the system SHALL validate that each prompt is properly formatted
3. WHEN running analysis THEN the system SHALL apply each prompt to every document independently
4. WHEN multiple prompts are used THEN the system SHALL organize results by prompt type and document
5. IF a prompt fails for a specific document THEN the system SHALL continue processing with remaining prompts

### Requirement 3

**User Story:** As a user, I want the system to handle LLM API calls efficiently and reliably, so that I can process large document sets without failures or excessive costs.

#### Acceptance Criteria

1. WHEN making LLM calls THEN the system SHALL use the nimble-llm-caller library for API management
2. WHEN processing multiple documents THEN the system SHALL implement rate limiting to avoid API throttling
3. WHEN API calls fail THEN the system SHALL implement retry logic with exponential backoff
4. WHEN processing large document sets THEN the system SHALL provide progress tracking and status updates
5. IF API quota is exceeded THEN the system SHALL pause processing and provide clear error messages

### Requirement 4

**User Story:** As a researcher, I want comprehensive statistics and analysis summaries, so that I can understand patterns and trends across the analyzed documents and across prompt sets.

#### Acceptance Criteria

1. WHEN analysis is complete THEN the system SHALL generate summary statistics for each prompt type
2. WHEN results are available THEN the system SHALL identify common themes and patterns across documents
3. WHEN generating reports THEN the system SHALL include document metadata (agency, title, date, etc.)
4. WHEN creating summaries THEN the system SHALL provide both individual document results and aggregate insights
5. WHEN analysis includes multiple agencies THEN the system SHALL enable comparison between agencies

### Requirement 5

**User Story:** As a user, I want flexible output formats and export options, so that I can integrate the analysis results with other tools and workflows.

#### Acceptance Criteria

1. WHEN analysis is complete THEN the system SHALL support multiple output formats (JSON, CSV, HTML report)
2. WHEN exporting results THEN the system SHALL include all prompt responses and metadata
3. WHEN generating reports THEN the system SHALL create human-readable summaries with visualizations
4. WHEN saving results THEN the system SHALL organize output files by timestamp and analysis configuration
5. IF export fails THEN the system SHALL provide fallback options and preserve analysis data

### Requirement 6

**User Story:** As a user, I want to resume interrupted analysis sessions, so that I don't lose progress when processing large document sets.

#### Acceptance Criteria

1. WHEN starting analysis THEN the system SHALL create a session state file to track progress
2. WHEN processing is interrupted THEN the system SHALL save completed analysis results
3. WHEN resuming a session THEN the system SHALL skip already processed documents
4. WHEN session state exists THEN the system SHALL offer to resume or start fresh
5. IF session state is corrupted THEN the system SHALL provide options to recover or restart

### Requirement 7

**User Story:** As an administrator, I want configurable analysis parameters and resource limits, so that I can control system usage and costs.

#### Acceptance Criteria

1. WHEN configuring analysis THEN the system SHALL accept limits on document count per agency
2. WHEN setting parameters THEN the system SHALL allow configuration of LLM model selection and parameters
3. WHEN running analysis THEN the system SHALL respect configured rate limits and timeouts
4. WHEN processing documents THEN the system SHALL provide cost estimation based on token usage
5. IF resource limits are exceeded THEN the system SHALL stop processing and provide clear notifications

### Requirement 8

**User Story:** As a user, I want to be able to run analysis sessions in parallel, so that I can process large document sets more efficiently.

#### Acceptance Criteria

1. WHEN starting analysis THEN the system SHALL support parallel processing of documents and prompts
2. WHEN processing multiple documents THEN the system SHALL distribute work across available CPU cores
3. WHEN running parallel analysis THEN the system SHALL maintain thread safety for shared resources
4. WHEN parallel processing is complete THEN the system SHALL aggregate results from all threads
5. IF parallel processing encounters errors THEN the system SHALL handle failures gracefully without affecting other threads

### Requirement 9

**User Story:** As a user, I want the system to closely emulate DOGE's analysis process, so that I can perform regulatory analysis consistent with DOGE methodology.  Authority: DOGE powerpoint published by Washington Post July 26, 2025.  https://www.washingtonpost.com/business/2025/07/26/doge-ai-tool-cut-regulations-trump/, link in article.

#### Acceptance Criteria

1. WHEN starting DOGE analysis THEN the system SHALL run a sequence of DOGE-emulation prompts against each document
2. WHEN running DOGE prompts THEN the system SHALL analyze regulation text to summarize content and identify core statutory provisions
3. WHEN categorizing regulations THEN the system SHALL classify each as Statutorily Required (SR), Not Statutorily Required (NSR), or Not Required but Agency Needs (NRAN)
4. WHEN categorization is SR or NSR THEN the system SHALL provide detailed explanation with reference to statute text
5. WHEN categorization is NRAN THEN the system SHALL provide explanation under categories of logical necessity, Article II powers, or resource efficiency
6. WHEN analyzing regulations THEN the system SHALL identify noncompliant statute subclauses and evaluate reform potential
7. WHEN running analysis THEN the system SHALL support multiple prompt packages prepared by different groups with different purposes

### Requirement 10

**User Story:** As a system administrator, I want several prompt packages to be available by default, so that users can choose from different analytical perspectives without creating custom prompts.

#### Acceptance Criteria

1. WHEN system initializes THEN the system SHALL include "DOGE emulation" prompt package as defined in Requirement 9
2. WHEN "Blue Dreams" package is selected THEN the system SHALL carry out analysis as if Democrats held the Presidency this term
3. WHEN "EO 14219" package is selected THEN the system SHALL follow Executive Order 14219 text from project root/data as faithfully as possible
4. WHEN "Technical Competence" package is selected THEN the system SHALL preserve federal agency technical competence while evaluating authorities and activities
5. WHEN selecting prompt packages THEN the system SHALL allow users to choose from all available default packages

### Requirement 11

**User Story:** As a project leader, I want the system to simulate the agency response phase of the DOGE analysis, so that I can model realistic agency feedback to reform recommendations.

#### Acceptance Criteria

1. WHEN DOGE analysis is complete THEN the system SHALL generate simulated agency responses for each recommendation
2. WHEN simulating agency responses THEN the system SHALL support multiple agency perspective types (fully aligned, fully resistant, partly resistant, bipartisan expert)
3. WHEN generating agency feedback THEN the system SHALL provide detailed rationale for each agency position
4. WHEN agency simulation is requested THEN the system SHALL allow selection of specific agency perspective types
5. IF agency response simulation fails THEN the system SHALL log errors and continue with remaining agencies

### Requirement 12

**User Story:** As a project leader, I want the system to simulate agency leadership responses to agency feedback, so that I can model the complete agency decision-making process.

#### Acceptance Criteria

1. WHEN agency feedback is complete THEN the system SHALL generate leadership responses from multiple perspectives
2. WHEN simulating leadership responses THEN the system SHALL support overrule, compromise, and alignment scenarios
3. WHEN generating leadership decisions THEN the system SHALL provide justification for each decision type
4. WHEN leadership simulation is complete THEN the system SHALL update recommendations based on leadership decisions
5. IF leadership simulation encounters errors THEN the system SHALL preserve agency feedback and continue processing

### Requirement 13

**User Story:** As a project leader, I want the system to create regulatory submission documents, so that I can implement recommendations after agency review and leadership approval.

#### Acceptance Criteria

1. WHEN agency review is complete THEN the system SHALL generate formal regulatory submission documents
2. WHEN creating submissions THEN the system SHALL include all required regulatory elements and justifications
3. WHEN generating documents THEN the system SHALL format submissions according to regulatory standards
4. WHEN submissions are created THEN the system SHALL include references to source analysis and agency feedback
5. IF document generation fails THEN the system SHALL provide error details and partial document recovery

### Requirement 14

**User Story:** As a project leader, I want the system to simulate public comment periods, so that I can model the complete regulatory process including public input.

#### Acceptance Criteria

1. WHEN regulatory submissions are ready THEN the system SHALL generate simulated public comments
2. WHEN creating public comments THEN the system SHALL simulate at least 100,000 diverse comment perspectives
3. WHEN generating comments THEN the system SHALL include various stakeholder viewpoints and comment types
4. WHEN comment simulation is complete THEN the system SHALL organize comments by theme and impact
5. IF comment generation exceeds resource limits THEN the system SHALL provide configurable comment volume controls

### Requirement 15

**User Story:** As a project leader, I want the system to analyze public comments, so that I can understand public sentiment and identify key concerns.

#### Acceptance Criteria

1. WHEN public comments are available THEN the system SHALL analyze all comments for themes and patterns
2. WHEN analyzing comments THEN the system SHALL categorize comments by support, opposition, and neutral positions
3. WHEN comment analysis is complete THEN the system SHALL identify the most frequently raised concerns
4. WHEN generating analysis THEN the system SHALL provide statistical summaries of comment sentiment
5. IF comment analysis fails THEN the system SHALL provide partial results and error reporting

### Requirement 16

**User Story:** As a project leader, I want the system to draft final rules with comment responses, so that I can complete the simulated regulatory process.

#### Acceptance Criteria

1. WHEN comment analysis is complete THEN the system SHALL draft final rule text incorporating public feedback
2. WHEN creating final rules THEN the system SHALL provide responses to significant public comments
3. WHEN generating rule responses THEN the system SHALL explain how comments were addressed or why they were not adopted
4. WHEN final rules are complete THEN the system SHALL include implementation timelines and compliance requirements
5. IF final rule drafting fails THEN the system SHALL preserve comment analysis and provide recovery options

### Requirement 17

**User Story:** As a system administrator, I want to selectively execute analysis stages and control processing volume, so that I can test and manage system resources effectively.

#### Acceptance Criteria

1. WHEN configuring analysis THEN the system SHALL allow selection of specific analysis stages to execute
2. WHEN setting processing limits THEN the system SHALL accept maximum document counts for each stage
3. WHEN running partial analysis THEN the system SHALL skip unselected stages and preserve intermediate results
4. WHEN stage selection is configured THEN the system SHALL provide clear indication of which stages will run
5. IF stage configuration is invalid THEN the system SHALL provide validation errors and suggested corrections


### Requirement 18

**User Story:** As a user, I want a web-based interface for document analysis, so that I can easily configure and monitor analysis sessions through a familiar interface.

#### Acceptance Criteria

1. WHEN accessing the system THEN the system SHALL provide a Streamlit-based web interface
2. WHEN using the web UI THEN the system SHALL allow configuration of all analysis parameters available in the CLI
3. WHEN running analysis through the web UI THEN the system SHALL provide real-time progress updates and status information
4. WHEN analysis is complete THEN the system SHALL display results and provide download options through the web interface
5. IF the web interface encounters errors THEN the system SHALL provide clear error messages and fallback to CLI options

