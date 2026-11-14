-- Existing embeddings from a different model cannot be converted meaningfully.
DO $$
BEGIN
    IF (SELECT atttypmod FROM pg_attribute WHERE attrelid = 'contract_embeddings'::regclass
        AND attname = 'embedding' AND NOT attisdropped) <> 384 THEN
        IF EXISTS (SELECT 1 FROM contract_embeddings WHERE embedding IS NOT NULL) THEN
            RAISE EXCEPTION 'Existing contract embeddings must be backed up and regenerated before changing dimensions to 384';
        END IF;
        DROP INDEX IF EXISTS idx_contract_embeddings_vector;
        ALTER TABLE contract_embeddings ALTER COLUMN embedding TYPE vector(384) USING embedding::vector(384);
    END IF;
END $$;

ALTER TABLE contract_embeddings ADD COLUMN IF NOT EXISTS chunk_id VARCHAR(100);
CREATE UNIQUE INDEX IF NOT EXISTS uq_contract_embeddings_user_contract_chunk
    ON contract_embeddings (user_id, contract_id, chunk_id);
CREATE INDEX IF NOT EXISTS idx_contract_embeddings_vector
    ON contract_embeddings USING hnsw (embedding vector_cosine_ops);
