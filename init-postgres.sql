-- Initialize PostgreSQL with vector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Add this to the top of init-postgres.sql
CREATE USER ollama_proxy WITH PASSWORD 'pass';

-- Then your existing code follows...
GRANT ALL ON FUNCTION public.first(anyelement, "any") TO ollama_proxy;