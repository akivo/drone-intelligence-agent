-- Runs once when the pgvector container first starts
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS flight_logs (
    id        SERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    drone_id  TEXT,
    content   TEXT,
    embedding vector(384)   -- all-MiniLM-L6-v2 output dimension
);
