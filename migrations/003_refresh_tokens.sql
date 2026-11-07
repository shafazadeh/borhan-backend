ALTER TABLE login_sessions ADD COLUMN IF NOT EXISTS refresh_token_hash CHAR(64);
ALTER TABLE login_sessions ADD COLUMN IF NOT EXISTS access_expires_at TIMESTAMPTZ;
CREATE UNIQUE INDEX IF NOT EXISTS login_sessions_refresh_token_hash_idx ON login_sessions(refresh_token_hash) WHERE refresh_token_hash IS NOT NULL;
