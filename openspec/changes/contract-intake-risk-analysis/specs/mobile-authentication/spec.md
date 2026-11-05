# Mobile Authentication

## Purpose

Provide a minimal mobile-number-based account and verified sign-in so users can securely access their own temporary contract sessions.

## ADDED Requirements

### Requirement: Mobile account identity
The system SHALL maintain a persistent user account identified by mobile number and retain only the account and authentication information needed for sign-in.

#### Scenario: First verified sign-in
- **WHEN** a mobile number is successfully verified for the first time
- **THEN** the system creates a user account for that number and authenticates the user

#### Scenario: Returning user
- **WHEN** a previously verified mobile number successfully signs in again
- **THEN** the system authenticates the existing account rather than creating a duplicate

### Requirement: Verify mobile number before sign-in
The system SHALL require a valid verification code before issuing an authentication credential for a mobile number.

#### Scenario: Incorrect code
- **WHEN** a user submits an incorrect verification code
- **THEN** the system denies authentication and does not issue a credential

### Requirement: Development-only verification code
The system SHALL accept the fixed code `1234` only when explicitly configured in development mode and SHALL disable sign-in outside development until a real SMS provider is configured.

#### Scenario: Development sign-in
- **WHEN** development mode is explicitly enabled and a user submits code `1234` for a mobile number
- **THEN** the system verifies the number for development sign-in

#### Scenario: Production without SMS provider
- **WHEN** the service runs outside development mode without a configured real SMS provider
- **THEN** sign-in is unavailable and the fixed development code is rejected

### Requirement: Authenticated contract operations
The system SHALL require a valid authenticated user credential for uploading, retrieving, or deleting a contract session.

#### Scenario: Missing or invalid credential
- **WHEN** an unauthenticated request attempts a contract session operation
- **THEN** the system rejects it without exposing session contents
