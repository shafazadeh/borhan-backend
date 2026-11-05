# Temporary Contract Sessions

## Purpose

Keep contract clauses and model results temporarily available to their authenticated owner for recovery after refresh or reconnection, with explicit deletion and automatic expiration.

## ADDED Requirements

### Requirement: User-owned temporary session
The system SHALL create a new session with an unpredictable identifier for each successfully analyzed upload and bind it to the authenticated user who uploaded it.

#### Scenario: Repeated upload
- **WHEN** the same user uploads the same document again
- **THEN** the system creates a separate session owned by that user

#### Scenario: Sign-in by a different user
- **WHEN** a different user signs in after a session is created
- **THEN** ownership of the existing session remains with the original user

### Requirement: Temporary memory-only storage
The system SHALL store session contents only in Redis configured without disk persistence, with a fixed lifetime of 7200 seconds from creation, and SHALL NOT log session identifiers.

#### Scenario: Session creation
- **WHEN** a completed analysis session is stored
- **THEN** its contract text and model responses are retained with an expiration of 7200 seconds

#### Scenario: Session expires
- **WHEN** 7200 seconds have elapsed since session creation
- **THEN** the session is no longer retrievable

### Requirement: Owner retrieves session
The system SHALL allow the authenticated owner to retrieve an unexpired session through `GET /api/v1/contracts/{contract_id}`.

#### Scenario: Owner returns after signing in again
- **WHEN** the original owner signs in again and requests an unexpired session
- **THEN** the system returns that session's clauses and model responses

#### Scenario: Different user requests a session
- **WHEN** an authenticated user requests a session owned by someone else
- **THEN** the system does not disclose its contents

#### Scenario: Session absent or expired
- **WHEN** the requested session is absent or expired
- **THEN** the system returns HTTP 404 with a message that the session has expired and the file must be uploaded again

### Requirement: Owner deletes session
The system SHALL allow the authenticated owner to immediately delete a session through `DELETE /api/v1/contracts/{contract_id}` and return HTTP 204 on successful deletion.

#### Scenario: Owner deletes an existing session
- **WHEN** the owner requests deletion of an unexpired session
- **THEN** the system removes the temporary session data and returns HTTP 204

#### Scenario: Different user attempts deletion
- **WHEN** an authenticated user attempts to delete another user's session
- **THEN** the system denies the operation and leaves that session intact
