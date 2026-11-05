# Contract Clause Analysis

## Purpose

Allow authenticated users to submit Persian contract documents and receive clause-by-clause responses from the existing risk model while keeping contract contents out of persistent storage.

## ADDED Requirements

### Requirement: Contract upload
The system SHALL accept a single PDF or DOCX file through `POST /api/v1/contracts/upload` from an authenticated user and SHALL enforce a 15 MB upload size limit.

#### Scenario: Supported document
- **WHEN** an authenticated user uploads one valid PDF or DOCX file within the size limit
- **THEN** the system proceeds to document extraction

#### Scenario: Oversized document
- **WHEN** the uploaded file exceeds 15 MB
- **THEN** the system rejects the upload without processing it with the model

### Requirement: Validate actual document type
The system SHALL validate document content as well as its declared type, and reject unsupported, malformed, password-protected, or unsafe files before analysis.

#### Scenario: Mismatched file type
- **WHEN** file contents do not match a supported PDF or DOCX document
- **THEN** the system rejects the upload with HTTP 415 or 422

#### Scenario: Unreadable document
- **WHEN** the document is corrupt or password-protected and cannot be extracted safely
- **THEN** the system rejects it with HTTP 415 or 422

### Requirement: Extract and segment Persian contract text
The system SHALL extract text, normalize common Persian character variants, and segment the extracted text into ordered clauses using Iranian legal document structure.

#### Scenario: Document with legal sections
- **WHEN** a document contains recognizable articles, clauses, or notes
- **THEN** the system returns ordered extracted clauses with distinct unpredictable clause identifiers and indexes

#### Scenario: No usable text
- **WHEN** a document contains no extractable contract text
- **THEN** the system reports an extraction failure and does not create a completed analysis session

### Requirement: Preserve model output
The system SHALL analyze each extracted clause with the configured model service and return its actual response for that clause without inventing classifications, reasons, or suggested wording.

#### Scenario: Model returns a response
- **WHEN** the model returns a response for a clause
- **THEN** the system includes that response in the corresponding clause result

#### Scenario: Model fails
- **WHEN** the model fails to analyze a clause
- **THEN** the system reports the failure and does not claim that the contract analysis completed successfully

### Requirement: Avoid persistent document content
The system SHALL process document contents without retaining raw files, filenames, contract text, or model results in permanent storage, and SHALL exclude contract text and filenames from logs.

#### Scenario: Processing succeeds or fails
- **WHEN** an upload is processed or processing fails
- **THEN** the system does not leave document contents in persistent storage or server logs
